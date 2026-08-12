from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from api.deps import get_current_user, require_hr_or_admin
from config.database import get_db
from ai.alert_generator import (
    generer_toutes_alertes,
    get_alertes,
    marquer_lue,
    get_stats_alertes
)
from ai.absenteeism_model import predire_absenteisme, entrainer_modele
from ai.anomaly_detector import (
    detecter_anomalies_pointage,
    detecter_employes_sans_pointage,
    detecter_retards_frequents
)
from datetime import datetime, timedelta

router = APIRouter()

# /ai exposes confidential HR analytics — risk scores, anomaly detection, model
# internals. Everything here is HR/admin except the personal alerts feed, which
# an employee needs for their own notification bell and which filters to their
# own record internally.
HR_ONLY = [Depends(require_hr_or_admin)]

# ============================================
# Générer alertes
# ============================================
@router.post("/generer-alertes", dependencies=HR_ONLY)
def generer_alertes(db: Session = Depends(get_db)):
    return generer_toutes_alertes(db)


# ============================================
# Alertes
# ============================================
@router.get("/alertes")
def get_all_alertes(
    non_lues: bool = False,
    limit: int = 50,
    employe_id: int = None,
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_user),
):
    """Alerts feed.

    HR and admins see everything and may filter by employee. An employee sees
    only their own alerts: the employe_id they send is ignored and replaced with
    their own, so they cannot read a colleague's risk profile by changing the ID
    in the URL.
    """
    if current["role"] not in ("rh", "admin"):
        own = current.get("employe_id")
        if not own:
            # A user account with no linked employee record has nothing to show.
            return []
        employe_id = own

    alertes = get_alertes(db, non_lues)
    if employe_id:
        alertes = [a for a in alertes if a.employe_id == employe_id]
    return [{
        "alerte_id"  : a.alerte_id,
        "employe_id" : a.employe_id,
        "type_alerte": a.type_alerte,
        "niveau"     : a.niveau,
        "message"    : a.message,
        "date_alerte": str(a.date_alerte),
        "est_lue"    : a.est_lue
    } for a in alertes[:limit]]


@router.get("/alertes/recentes", dependencies=HR_ONLY)
def alertes_recentes(heures: int = 24, db: Session = Depends(get_db)):
    """Alertes des dernières N heures"""
    from models.models import AlerteIA
    depuis = datetime.now() - timedelta(hours=heures)
    alertes = db.query(AlerteIA).filter(
        AlerteIA.date_alerte >= depuis
    ).order_by(AlerteIA.date_alerte.desc()).all()
    return [{
        "alerte_id"  : a.alerte_id,
        "employe_id" : a.employe_id,
        "type_alerte": a.type_alerte,
        "niveau"     : a.niveau,
        "message"    : a.message,
        "date_alerte": str(a.date_alerte),
        "est_lue"    : a.est_lue
    } for a in alertes]


@router.get("/alertes/stats", dependencies=HR_ONLY)
def stats_alertes(db: Session = Depends(get_db)):
    return get_stats_alertes(db)


@router.put("/alertes/{alerte_id}/lue")
def marquer_alerte_lue(
    alerte_id: int,
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_user),
):
    """Dismiss an alert. An employee may only dismiss their own."""
    if current["role"] not in ("rh", "admin"):
        from models.models import AlerteIA
        alerte = db.query(AlerteIA).filter(AlerteIA.alerte_id == alerte_id).first()
        if not alerte:
            raise HTTPException(status_code=404, detail="Alerte introuvable")
        if alerte.employe_id != current.get("employe_id"):
            raise HTTPException(status_code=403, detail="Not your alert")
    return marquer_lue(db, alerte_id)


# ============================================
# Prédiction absentéisme
# ============================================
@router.get("/prediction-absenteisme", dependencies=HR_ONLY)
def prediction_absenteisme(db: Session = Depends(get_db)):
    # Routed through the gate: serves the ML model only where it has been shown
    # to beat the rule-based baseline on this database, and the rule otherwise.
    # Calling predire_absenteisme directly would serve the v1 model regardless
    # of whether it is any good — and on stable-behaviour data it is not.
    from ai.model_gate import predict as gated_predict
    return gated_predict(db)


# Alias pour utils.py
@router.get("/employes-a-risque", dependencies=HR_ONLY)
def employes_a_risque(db: Session = Depends(get_db)):
    # Routed through the gate: serves the ML model only where it has been shown
    # to beat the rule-based baseline on this database, and the rule otherwise.
    # Calling predire_absenteisme directly would serve the v1 model regardless
    # of whether it is any good — and on stable-behaviour data it is not.
    from ai.model_gate import predict as gated_predict
    return gated_predict(db)


@router.post("/entrainer-modele", dependencies=HR_ONLY)
def entrainer(db: Session = Depends(get_db)):
    return entrainer_modele(db)


# ============================================
# Model v2 — deterioration ("who is getting worse")
# ============================================
@router.post("/entrainer-modele-v2", dependencies=HR_ONLY)
def entrainer_v2(db: Session = Depends(get_db)):
    """Train the v2 model. Run from the scheduler, not on every request."""
    from ai.risk_model import train_risk_model
    return train_risk_model(db)


@router.get("/model-info-v2", dependencies=HR_ONLY)
def model_info_v2():
    """v2 metrics, including whether it actually beats the rule-based baseline."""
    from ai.risk_model import load_metrics, model_available
    m = load_metrics()
    if not m:
        return {"trained": False, "available": model_available()}
    return {"trained": True, "available": model_available(), **m}


@router.post("/entrainer-gate", dependencies=HR_ONLY)
def entrainer_gate(db: Session = Depends(get_db)):
    """Train and decide whether the model is worth using on THIS database.

    Checks there is enough history to answer the question, trains, scores
    against the rule-based baseline on a held-out temporal split, and only
    promotes the model if it wins by a margin. A verdict of "baseline" is a
    valid outcome, not a failure.
    """
    from ai.model_gate import train_and_gate
    return train_and_gate(db)


@router.get("/strategy", dependencies=HR_ONLY)
def risk_strategy(db: Session = Depends(get_db)):
    """Which predictor is serving risk scores, and why."""
    from ai.model_gate import check_data_sufficiency, read_gate
    return {**read_gate(), "current_data": check_data_sufficiency(db)}


@router.get("/model-info", dependencies=HR_ONLY)
def get_model_info():
    """Return last training metrics + feature importances (no DB needed)."""
    import json, os
    metrics_path = "ai/models/model_metrics.json"
    if not os.path.exists(metrics_path):
        return {"trained": False}
    with open(metrics_path) as f:
        info = json.load(f)
    info["trained"] = True
    return info


# ============================================
# Anomalies
# ============================================
@router.get("/anomalies-pointage", dependencies=HR_ONLY)
def anomalies_pointage(db: Session = Depends(get_db)):
    return detecter_anomalies_pointage(db)


# Alias pour utils.py
@router.get("/anomalies", dependencies=HR_ONLY)
def anomalies(db: Session = Depends(get_db)):
    return detecter_anomalies_pointage(db)


@router.get("/sans-pointage", dependencies=HR_ONLY)
def sans_pointage(db: Session = Depends(get_db)):
    return detecter_employes_sans_pointage(db)


@router.get("/retards-frequents", dependencies=HR_ONLY)
def retards_frequents(seuil: int = 3, db: Session = Depends(get_db)):
    return detecter_retards_frequents(db, seuil)


# ============================================
# Prédiction par employé
# ============================================
@router.get("/prediction/{employe_id}", dependencies=HR_ONLY)
def prediction_employe(employe_id: int, db: Session = Depends(get_db)):
    """Prédiction absentéisme pour un employé spécifique"""
    from ai.model_gate import predict as gated_predict
    tous = gated_predict(db)
    for emp in tous:
        if emp["employe_id"] == employe_id:
            return emp
    return {"employe_id": employe_id, "probabilite": 0, "niveau": "Faible", "message": "Pas de risque détecté"}