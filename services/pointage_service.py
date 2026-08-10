from sqlalchemy.orm import Session
from repositories import pointage_repo
from models.models import Absence
from datetime import datetime, date, timedelta

# ============================================
# Service - Pointage
# ============================================

def pointer(db: Session, employe_id: int):
    """
    Enregistrer un pointage (entrée ou sortie)
    Retourne le log créé ou None si doublon
    """
    log = pointage_repo.add_pointage_log(db, employe_id)
    if not log:
        return {"message": "Doublon ignoré (badge trop rapide)", "log": None}
    return {"message": f"Pointage {log.type_pointage} enregistré", "log": log}


def get_historique(db: Session, employe_id: int, limit: int = 30):
    """Récupérer l'historique de pointage"""
    return pointage_repo.get_historique_pointage(db, employe_id, limit)


def get_pointages_periode(db: Session, employe_id: int, date_debut: date, date_fin: date):
    """Récupérer les pointages sur une période"""
    return pointage_repo.get_pointages_periode(db, employe_id, date_debut, date_fin)


def get_all_today(db: Session):
    """Récupérer tous les pointages du jour (vue RH)"""
    return pointage_repo.get_all_pointages_today(db)


def calculer_heures_mois(db: Session, employe_id: int, annee: int, mois: int):
    """
    Calculer les heures totales travaillées dans un mois
    """
    date_debut = date(annee, mois, 1)
    if mois == 12:
        date_fin = date(annee + 1, 1, 1) - timedelta(days=1)
    else:
        date_fin = date(annee, mois + 1, 1) - timedelta(days=1)

    pointages = pointage_repo.get_pointages_periode(db, employe_id, date_debut, date_fin)

    total_heures   = sum(p.duree_travail or 0 for p in pointages)
    total_retards  = sum(p.retard_minutes or 0 for p in pointages)
    jours_presents = len([p for p in pointages if p.statut in ["Present", "En retard"]])
    jours_absents  = len([p for p in pointages if p.statut == "Absent"])

    return {
        "total_heures"   : round(total_heures, 2),
        "total_retards"  : total_retards,
        "jours_presents" : jours_presents,
        "jours_absents"  : jours_absents,
        "nb_pointages"   : len(pointages)
    }


def detecter_absences(db: Session, employe_id: int, date_debut: date, date_fin: date):
    """
    Détecter les jours ouvrables sans pointage
    et les enregistrer comme absences
    """
    pointages = pointage_repo.get_pointages_periode(db, employe_id, date_debut, date_fin)
    jours_pointes = {p.date_pointage for p in pointages}

    # Jours fériés : personne ne pointe, ce ne sont pas des absences.
    # Sans ce filtre, l'Aïd génère une absence pour tout l'effectif et fausse
    # à la fois les statistiques et le modèle d'absentéisme.
    try:
        from services.holiday_service import holiday_dates
        feries = holiday_dates(db, date_debut, date_fin)
    except Exception:
        feries = set()

    absences_creees = []
    current = date_debut

    while current <= date_fin:
        # Ignorer weekends et jours fériés
        if current.weekday() < 5 and current not in feries and current not in jours_pointes:
            # Vérifier si absence déjà enregistrée
            existing = db.query(Absence).filter(
                Absence.employe_id  == employe_id,
                Absence.date_absence == current
            ).first()

            if not existing:
                absence = Absence(
                    employe_id   = employe_id,
                    date_absence = current,
                    justifiee    = False,
                    statut       = "Non justifiée"
                )
                db.add(absence)
                absences_creees.append(current)

        current += timedelta(days=1)

    db.commit()
    return absences_creees


def get_taux_presence_mois(db: Session, employe_id: int, annee: int, mois: int):
    """
    Calculer le taux de présence d'un employé pour un mois
    """
    stats = calculer_heures_mois(db, employe_id, annee, mois)
    total_jours = stats["jours_presents"] + stats["jours_absents"]

    if total_jours == 0:
        return 0.0

    taux = (stats["jours_presents"] / total_jours) * 100
    return round(taux, 2)