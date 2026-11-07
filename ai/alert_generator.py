"""
ai/alert_generator.py - composes the AI alerts shown on the HR dashboard.

Improvements over the previous version:
  * messages are in **English** (the rest of the UI is English-only, so the
    French strings used to leak into a clean interface);
  * the same employee never receives duplicate active alerts of the same
    type - before writing, we drop the previous *unread* alert of the same
    (employe_id, type_alerte) tuple so the bell shows a single, current
    line per situation instead of a growing list of identical entries;
  * messages are **actionable** - they end with the HR action that follows
    from the signal (schedule a meeting, ask for a justification, ...) so
    the manager opens the alert and already knows what to do;
  * an upper bound per category prevents one busy day from filling the
    dashboard with 200 anomaly lines;
  * the absenteeism-risk alert now carries the predicted probability with
    a single decimal place and rounds the count fields, matching the
    crisp look the rest of the dashboard uses.
"""
from datetime import datetime
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.models import AlerteIA, Employe
from ai.absenteeism_model import predire_absenteisme
from ai.anomaly_detector import (
    detecter_anomalies_pointage,
    detecter_employes_sans_pointage,
    detecter_retards_frequents,
)

logger = logging.getLogger(__name__)


# Caps so the dashboard stays readable even when the simulator goes wide.
MAX_ABSENTEEISM_ALERTS = 12
MAX_ANOMALY_ALERTS     = 8
MAX_NO_PUNCH_ALERTS    = 8
MAX_LATE_ALERTS        = 8


# Executive / top-management postes whose holders are not subject to the
# same attendance scrutiny as regular employees. Generating an absenteeism
# alert about the CEO would be both inaccurate (their schedule is not on
# the time-clock) and embarrassing during a demo. Add any new title here.
EXECUTIVE_POSTES = {
    "PDG",
    "CEO",
    "Director",
    "Directeur",
    "Directeur Financier",
    "Directeur Général",
    "Directeur General",
    "Directrice",
    "Deputy General Manager (DGA)",
    "DGA",
    "Gérant",
    "Gerant",
}


def _excluded_employee_ids(db: Session) -> set[int]:
    """Set of employe_id values that must be skipped by every alert path.

    Matching is case-insensitive and substring-based so a poste like
    'Senior Director - Operations' is still caught by 'Director'.
    """
    rows = db.query(Employe.employe_id, Employe.poste).all()
    keys = [k.upper() for k in EXECUTIVE_POSTES]
    excluded: set[int] = set()
    for emp_id, poste in rows:
        if not poste:
            continue
        up = poste.upper()
        if any(k in up for k in keys):
            excluded.add(int(emp_id))
    return excluded


# ──────────────────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────────────────
def _employee_display(db: Session, employe_id: int, fallback: str = "") -> str:
    """Return 'PRÉNOM NOM (matricule)' or whatever we can find."""
    if fallback:
        return fallback
    e = db.query(Employe).filter(Employe.employe_id == employe_id).first()
    if not e:
        return f"Employee #{employe_id}"
    parts = [p for p in (e.prenom, e.nom) if p]
    name  = " ".join(parts) if parts else f"Employee #{employe_id}"
    return f"{name} ({e.matricule})" if getattr(e, "matricule", None) else name


def _upsert(db: Session, employe_id: int, type_alerte: str, niveau: str, message: str):
    """Replace the unread alert of the same (employee, type) - never duplicate."""
    existing = db.query(AlerteIA).filter(
        and_(
            AlerteIA.employe_id == employe_id,
            AlerteIA.type_alerte == type_alerte,
            AlerteIA.est_lue == False,  # noqa: E712 (SQLAlchemy compares to False, not 'is False')
        )
    ).all()
    for old in existing:
        db.delete(old)
    db.add(AlerteIA(
        employe_id  = employe_id,
        type_alerte = type_alerte,
        niveau      = niveau,
        message     = message,
        est_lue     = False,
    ))


# ──────────────────────────────────────────────────────────────────────
# public API - unchanged signatures so the schedulers keep working
# ──────────────────────────────────────────────────────────────────────
def generer_toutes_alertes(db: Session):
    """Regenerate the AI alerts and return a summary dict."""
    summary: list[dict] = []
    excluded = _excluded_employee_ids(db)
    if excluded:
        logger.info("Excluding %d executive(s) from alert generation: %s",
                    len(excluded), sorted(excluded))

    # ── 1. Absenteeism-risk predictions ──────────────────────────────
    try:
        risk = [e for e in predire_absenteisme(db)
                if int(e.get("employe_id", -1)) not in excluded]
        # Highest-risk first, capped, so the bell is dominated by signal.
        risk.sort(key=lambda e: e.get("probabilite", 0), reverse=True)
        for emp in risk[:MAX_ABSENTEEISM_ALERTS]:
            name   = _employee_display(db, emp["employe_id"], fallback=emp.get("nom", ""))
            prob   = round(float(emp.get("probabilite", 0)), 1)
            nb_abs = int(emp.get("nb_absences", 0))
            nb_ret = int(emp.get("nb_retards", 0))
            # Explainability: lead with the model's top driver so the alert
            # says *why*, not just *how much*.
            raisons = emp.get("raisons") or []
            if raisons:
                driver = "Main driver: " + raisons[0]["text"] + ". "
            else:
                driver = ""
            msg = (
                f"{name} - absenteeism risk {prob:.1f}% "
                f"({nb_abs} absence{'s' if nb_abs > 1 else ''}, "
                f"{nb_ret} late{'s' if nb_ret > 1 else ''}). "
                f"{driver}"
                "Schedule a one-on-one to understand the cause before it escalates."
            )
            _upsert(db, emp["employe_id"], "Absenteeism risk", emp["niveau"], msg)
            summary.append({"type": "Absenteeism", "niveau": emp["niveau"], "message": msg})
    except Exception as e:
        logger.error("Absenteeism alerts failed: %s", e)

    # ── 2. Punch anomalies (Isolation Forest) ────────────────────────
    try:
        anomalies = [a for a in (detecter_anomalies_pointage(db) or [])
                     if int(a.get("employe_id", -1)) not in excluded]
        # Critique > Moyen > Info so the dashboard surfaces the worst first.
        prio = {"Critique": 0, "Moyen": 1, "Info": 2}
        anomalies.sort(key=lambda a: prio.get(a.get("niveau", "Info"), 99))
        for anom in anomalies[:MAX_ANOMALY_ALERTS]:
            name = _employee_display(db, anom["employe_id"])
            type_label = {
                "Pointage hors horaires (nuit)"      : "punch outside working hours",
                "Pointage weekend"                   : "punch recorded on a weekend",
                "Pointage très tôt le matin"         : "very early-morning punch",
                "Comportement de pointage inhabituel": "unusual punch pattern",
            }.get(anom.get("type_anomalie"), "abnormal punch pattern")
            hour = anom.get("heure", "-")
            msg = (
                f"{name} - {type_label} at {hour}h. "
                "Review the punch log and contact the employee if it persists."
            )
            _upsert(db, anom["employe_id"], "Punch anomaly", anom["niveau"], msg)
            summary.append({"type": "Anomaly", "niveau": anom["niveau"], "message": msg})
    except Exception as e:
        logger.error("Punch-anomaly alerts failed: %s", e)

    # ── 3. No-punch-today (most urgent operational signal) ───────────
    try:
        sans_pointage = [e for e in (detecter_employes_sans_pointage(db) or [])
                         if int(e.get("employe_id", -1)) not in excluded]
        for emp in sans_pointage[:MAX_NO_PUNCH_ALERTS]:
            name = _employee_display(db, emp["employe_id"], fallback=emp.get("nom", ""))
            msg = (
                f"{name} - no punch recorded today. "
                "Confirm presence, otherwise log an unjustified absence."
            )
            _upsert(db, emp["employe_id"], "No punch today", "Critique", msg)
            summary.append({"type": "No punch", "niveau": "Critique", "message": msg})
    except Exception as e:
        logger.error("No-punch alerts failed: %s", e)

    # ── 4. Frequent lateness this month ──────────────────────────────
    try:
        retards = [e for e in (detecter_retards_frequents(db, seuil=3) or [])
                   if int(e.get("employe_id", -1)) not in excluded]
        retards.sort(key=lambda e: e.get("nb_retards", 0), reverse=True)
        for emp in retards[:MAX_LATE_ALERTS]:
            name   = _employee_display(db, emp["employe_id"], fallback=emp.get("nom", ""))
            nb_ret = int(emp.get("nb_retards", 0))
            msg = (
                f"{name} - {nb_ret} late arrival{'s' if nb_ret > 1 else ''} this month. "
                "Consider a formal reminder of the company schedule."
            )
            _upsert(db, emp["employe_id"], "Frequent lateness", emp["niveau"], msg)
            summary.append({"type": "Lateness", "niveau": emp["niveau"], "message": msg})
    except Exception as e:
        logger.error("Frequent-lateness alerts failed: %s", e)

    db.commit()
    return {"total_alertes": len(summary), "alertes": summary, "generated_at": datetime.utcnow().isoformat()}


# ──────────────────────────────────────────────────────────────────────
# Reader helpers - signatures unchanged so the routes keep working.
# ──────────────────────────────────────────────────────────────────────
def get_alertes(db: Session, non_lues_seulement: bool = False):
    query = db.query(AlerteIA)
    if non_lues_seulement:
        query = query.filter(AlerteIA.est_lue == False)  # noqa: E712
    return query.order_by(AlerteIA.date_alerte.desc()).limit(50).all()


def marquer_lue(db: Session, alerte_id: int):
    alerte = db.query(AlerteIA).filter(AlerteIA.alerte_id == alerte_id).first()
    if alerte:
        alerte.est_lue = True
        db.commit()
    return alerte


def get_stats_alertes(db: Session):
    total     = db.query(AlerteIA).count()
    non_lues  = db.query(AlerteIA).filter(AlerteIA.est_lue == False).count()  # noqa: E712
    critiques = db.query(AlerteIA).filter(AlerteIA.niveau == "Critique").count()
    moyens    = db.query(AlerteIA).filter(AlerteIA.niveau == "Moyen").count()
    return {"total": total, "non_lues": non_lues, "critiques": critiques, "moyens": moyens}
