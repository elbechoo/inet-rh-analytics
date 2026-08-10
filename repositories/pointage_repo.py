from sqlalchemy.orm import Session
from models.models import Pointage, PointageLog
from datetime import datetime, date, timedelta, time
from typing import List, Optional

# ============================================
# Configuration horaires
# ============================================
HEURE_ENTREE_NORMALE  = time(8, 0)    # 08:00
HEURE_PAUSE_DEBUT     = time(12, 0)   # 12:00
HEURE_PAUSE_FIN       = time(13, 0)   # 13:00
HEURE_SORTIE_NORMALE  = time(17, 0)   # 17:00
SEUIL_RETARD_MINUTES  = 15            # tolérance retard
SEUIL_NUIT            = time(22, 0)   # début shift nuit


# ============================================
# ALGORITHME PRINCIPAL - Déterminer ENTREE/SORTIE
# ============================================
def determiner_type_pointage(timestamp: datetime, logs_existants: list) -> str:
    if not logs_existants:
        return "ENTREE"

    dernier_log = logs_existants[-1]
    diff_minutes = (timestamp - dernier_log.timestamp_pointage).total_seconds() / 60
    if diff_minutes < 2:
        return "DOUBLON"

    sequence = ["ENTREE", "DEBUT_PAUSE", "FIN_PAUSE", "SORTIE"]
    nb_logs = len(logs_existants)

    if nb_logs >= 4:
        return "DOUBLON"  # journée déjà complète

    return sequence[nb_logs]


# ============================================
# Ajouter un log de pointage
# ============================================
def add_pointage_log(db: Session, employe_id: int) -> Optional[PointageLog]:
    """
    Enregistrer un badge avec détection automatique ENTREE/SORTIE
    """
    now = datetime.now()
    today = now.date()

    # Pour shift nuit: chercher depuis hier 22h
    hier = today - timedelta(days=1)
    depuis = datetime.combine(hier, SEUIL_NUIT) if now.time() < time(6, 0) else datetime.combine(today, time(0, 0))

    logs_existants = db.query(PointageLog).filter(
        PointageLog.employe_id == employe_id,
        PointageLog.timestamp_pointage >= depuis,
        PointageLog.timestamp_pointage <= now
    ).order_by(PointageLog.timestamp_pointage).all()

    # Déterminer le type
    type_pointage = determiner_type_pointage(now, logs_existants)

    # Ignorer les doublons
    if type_pointage == "DOUBLON":
        return None

    # Enregistrer le log
    log = PointageLog(
        employe_id=employe_id,
        timestamp_pointage=now,
        type_pointage=type_pointage,
        source="pointeuse"
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    # Recalculer le résumé journalier
    _update_pointage_journalier(db, employe_id, today)

    return log


# ============================================
# Recalculer le résumé journalier
# ============================================
def _update_pointage_journalier(db: Session, employe_id: int, today: date):
    hier   = today - timedelta(days=1)
    depuis = datetime.combine(hier, SEUIL_NUIT)
    jusqua = datetime.combine(today, time(23, 59, 59))

    logs = db.query(PointageLog).filter(
        PointageLog.employe_id == employe_id,
        PointageLog.timestamp_pointage >= depuis,
        PointageLog.timestamp_pointage <= jusqua
    ).order_by(PointageLog.timestamp_pointage).all()

    if not logs:
        return

    # Extraire chaque type
    def get_time(type_p):
        l = next((x for x in logs if x.type_pointage == type_p), None)
        return l.timestamp_pointage.time() if l else None

    heure_entree      = get_time("ENTREE")
    heure_debut_pause = get_time("DEBUT_PAUSE")
    heure_fin_pause   = get_time("FIN_PAUSE")
    heure_sortie      = get_time("SORTIE")

    # Calcul durée (entrée→debut_pause) + (fin_pause→sortie)
    duree_totale = timedelta(0)
    if heure_entree and heure_debut_pause:
        d1 = datetime.combine(today, heure_debut_pause) - datetime.combine(today, heure_entree)
        if d1.total_seconds() > 0:
            duree_totale += d1
    elif heure_entree and heure_sortie and not heure_debut_pause:
        # Pas de pause
        d1 = datetime.combine(today, heure_sortie) - datetime.combine(today, heure_entree)
        if d1.total_seconds() > 0:
            duree_totale += d1

    if heure_fin_pause and heure_sortie:
        d2 = datetime.combine(today, heure_sortie) - datetime.combine(today, heure_fin_pause)
        if d2.total_seconds() > 0:
            duree_totale += d2

    duree_heures = round(duree_totale.total_seconds() / 3600, 2)

    # Retard
    retard_minutes = 0
    if heure_entree:
        entree_dt  = datetime.combine(today, heure_entree)
        normale_dt = datetime.combine(today, HEURE_ENTREE_NORMALE)
        if entree_dt > normale_dt:
            retard_minutes = int((entree_dt - normale_dt).total_seconds() / 60)

    # Statut
    nb_logs = len(logs)
    if nb_logs == 4:
        statut = "En retard" if retard_minutes > SEUIL_RETARD_MINUTES else "Présent"
    elif heure_entree and not heure_sortie:
        statut = "Sortie manquante"
    else:
        statut = "En retard" if retard_minutes > SEUIL_RETARD_MINUTES else "Présent"

    # Sauvegarder
    pointage = db.query(Pointage).filter(
        Pointage.employe_id == employe_id,
        Pointage.date_pointage == today
    ).first()

    vals = dict(
        heure_entree=heure_entree,
        heure_debut_pause=heure_debut_pause,
        heure_fin_pause=heure_fin_pause,
        heure_sortie=heure_sortie,
        duree_travail=duree_heures,
        retard_minutes=retard_minutes,
        statut=statut
    )

    if pointage:
        for k, v in vals.items():
            setattr(pointage, k, v)
    else:
        pointage = Pointage(employe_id=employe_id, date_pointage=today, **vals)
        db.add(pointage)

    db.commit()
    return pointage

# ============================================
# Getters
# ============================================
def get_pointage_by_employe(db: Session, employe_id: int):
    return db.query(Pointage).filter(
        Pointage.employe_id == employe_id
    ).order_by(Pointage.date_pointage.desc()).all()


def get_historique_pointage(db: Session, employe_id: int, limit: int = 30):
    return db.query(Pointage).filter(
        Pointage.employe_id == employe_id
    ).order_by(Pointage.date_pointage.desc()).limit(limit).all()


def get_pointages_periode(db: Session, employe_id: int, date_debut: date, date_fin: date):
    return db.query(Pointage).filter(
        Pointage.employe_id == employe_id,
        Pointage.date_pointage >= date_debut,
        Pointage.date_pointage <= date_fin
    ).order_by(Pointage.date_pointage).all()


def get_all_pointages_today(db: Session):
    today = date.today()
    return db.query(Pointage).filter(
        Pointage.date_pointage == today
    ).all()