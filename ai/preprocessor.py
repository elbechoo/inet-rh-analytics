import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from models.models import Employe, Pointage, PointageLog, Absence, Conge
from datetime import datetime, date, timedelta
from typing import Optional

# ============================================
# Preprocessor - Préparer les données pour l'IA
# ============================================

def get_pointage_dataframe(db: Session) -> pd.DataFrame:
    pointages = db.query(Pointage).all()
    if not pointages:
        return pd.DataFrame()
    data = []
    for p in pointages:
        data.append({
            "employe_id"    : p.employe_id,
            "date"          : p.date_pointage,
            "heure_entree"  : p.heure_entree,
            "heure_sortie"  : p.heure_sortie,
            "duree_travail" : p.duree_travail or 0,
            "retard_minutes": p.retard_minutes or 0,
            "statut"        : p.statut or "Inconnu",
            "jour_semaine"  : p.date_pointage.weekday() if p.date_pointage else 0,
            "mois"          : p.date_pointage.month if p.date_pointage else 0,
        })
    return pd.DataFrame(data)


def get_employe_features(db: Session) -> pd.DataFrame:
    employes = db.query(Employe).filter(Employe.statut == "Actif").all()
    if not employes:
        return pd.DataFrame()

    features = []
    for emp in employes:
        pointages = db.query(Pointage).filter(
            Pointage.employe_id == emp.employe_id
        ).all()
        absences = db.query(Absence).filter(
            Absence.employe_id == emp.employe_id
        ).all()
        conges = db.query(Conge).filter(
            Conge.employe_id == emp.employe_id,
            Conge.statut     == "Approuvé"
        ).all()

        nb_pointages       = len(pointages)
        nb_absences        = len(absences)
        nb_absences_injust = len([a for a in absences if not a.justifiee])
        nb_retards         = len([p for p in pointages if p.statut == "En retard"])
        nb_conges          = len(conges)
        total_heures       = sum(p.duree_travail or 0 for p in pointages)
        total_retard_min   = sum(p.retard_minutes or 0 for p in pointages)
        moy_heures         = total_heures / nb_pointages if nb_pointages > 0 else 0
        moy_retard         = total_retard_min / nb_pointages if nb_pointages > 0 else 0
        taux_absence       = nb_absences / max(nb_pointages + nb_absences, 1)
        taux_retard        = nb_retards / max(nb_pointages, 1)

        if emp.date_embauche:
            anciennete = (date.today() - emp.date_embauche).days / 365
        else:
            anciennete = 0

        features.append({
            "employe_id"        : emp.employe_id,
            "matricule"         : emp.matricule,
            "nom"               : f"{emp.prenom} {emp.nom}",
            "departement_id"    : emp.departement_id,
            "anciennete"        : round(anciennete, 2),
            "nb_pointages"      : nb_pointages,
            "nb_absences"       : nb_absences,
            "nb_absences_injust": nb_absences_injust,
            "nb_retards"        : nb_retards,
            "nb_conges"         : nb_conges,
            "total_heures"      : round(total_heures, 2),
            "moy_heures_jour"   : round(moy_heures, 2),
            "moy_retard_min"    : round(moy_retard, 2),
            "taux_absence"      : round(taux_absence, 4),
            "taux_retard"       : round(taux_retard, 4),
        })

    return pd.DataFrame(features)


def get_employe_features_periode(
    db: Session,
    date_debut: date,
    date_fin: date,
    min_activite: int = 10,
) -> pd.DataFrame:
    """
    Compute per-employee behavioural features restricted to [date_debut, date_fin].

    Used for temporal validation: train features come from an earlier period,
    label features come from a later period — avoiding data leakage.

    Employees with fewer than `min_activite` attendance+absence records in the
    period are excluded (not enough signal).
    """
    employes = db.query(Employe).filter(Employe.statut == "Actif").all()
    if not employes:
        return pd.DataFrame()

    features = []
    for emp in employes:
        pointages = db.query(Pointage).filter(
            Pointage.employe_id    == emp.employe_id,
            Pointage.date_pointage >= date_debut,
            Pointage.date_pointage <= date_fin,
        ).all()
        absences = db.query(Absence).filter(
            Absence.employe_id  == emp.employe_id,
            Absence.date_absence >= date_debut,
            Absence.date_absence <= date_fin,
        ).all()
        conges = db.query(Conge).filter(
            Conge.employe_id  == emp.employe_id,
            Conge.statut      == "Approuvé",
            Conge.date_debut  >= date_debut,
            Conge.date_debut  <= date_fin,
        ).all()

        nb_pointages       = len(pointages)
        nb_absences        = len(absences)

        if nb_pointages + nb_absences < min_activite:
            continue

        nb_absences_injust = len([a for a in absences if not a.justifiee])
        nb_retards         = len([p for p in pointages if p.statut == "En retard"])
        nb_conges          = len(conges)
        total_heures       = sum(p.duree_travail or 0 for p in pointages)
        total_retard_min   = sum(p.retard_minutes or 0 for p in pointages)
        moy_heures         = total_heures / nb_pointages if nb_pointages else 0
        moy_retard         = total_retard_min / nb_pointages if nb_pointages else 0
        taux_absence       = nb_absences / max(nb_pointages + nb_absences, 1)
        taux_retard        = nb_retards / max(nb_pointages, 1)
        anciennete         = (date_fin - emp.date_embauche).days / 365 if emp.date_embauche else 0

        features.append({
            "employe_id"        : emp.employe_id,
            "matricule"         : emp.matricule,
            "nom"               : f"{emp.prenom} {emp.nom}",
            "departement_id"    : emp.departement_id,
            "anciennete"        : round(anciennete, 2),
            "nb_pointages"      : nb_pointages,
            "nb_absences"       : nb_absences,
            "nb_absences_injust": nb_absences_injust,
            "nb_retards"        : nb_retards,
            "nb_conges"         : nb_conges,
            "total_heures"      : round(total_heures, 2),
            "moy_heures_jour"   : round(moy_heures, 2),
            "moy_retard_min"    : round(moy_retard, 2),
            "taux_absence"      : round(taux_absence, 4),
            "taux_retard"       : round(taux_retard, 4),
        })

    return pd.DataFrame(features)


def get_pointagelog_dataframe(db: Session) -> pd.DataFrame:
    """
    Récupérer les logs bruts - utilise PointageLog si disponible,
    sinon fallback sur Pointage traité
    """
    # Essayer PointageLog d'abord
    logs = db.query(PointageLog).all()

    if logs:
        data = []
        for log in logs:
            ts = log.timestamp_pointage
            data.append({
                "employe_id"   : log.employe_id,
                "timestamp"    : ts,
                "type_pointage": log.type_pointage,
                "heure"        : ts.hour if ts else 0,
                "minute"       : ts.minute if ts else 0,
                "jour_semaine" : ts.weekday() if ts else 0,
                "heure_decimal": ts.hour + ts.minute / 60 if ts else 0,
            })
        return pd.DataFrame(data)

    # Fallback: utiliser Pointage traité
    pointages = db.query(Pointage).all()
    if not pointages:
        return pd.DataFrame()

    data = []
    for p in pointages:
        if p.heure_entree and p.date_pointage:
            ts_entree = datetime.combine(p.date_pointage, p.heure_entree)
            data.append({
                "employe_id"   : p.employe_id,
                "timestamp"    : ts_entree,
                "type_pointage": "ENTREE",
                "heure"        : p.heure_entree.hour,
                "minute"       : p.heure_entree.minute,
                "jour_semaine" : p.date_pointage.weekday(),
                "heure_decimal": p.heure_entree.hour + p.heure_entree.minute / 60,
            })
        if p.heure_sortie and p.date_pointage:
            ts_sortie = datetime.combine(p.date_pointage, p.heure_sortie)
            data.append({
                "employe_id"   : p.employe_id,
                "timestamp"    : ts_sortie,
                "type_pointage": "SORTIE",
                "heure"        : p.heure_sortie.hour,
                "minute"       : p.heure_sortie.minute,
                "jour_semaine" : p.date_pointage.weekday(),
                "heure_decimal": p.heure_sortie.hour + p.heure_sortie.minute / 60,
            })

    return pd.DataFrame(data)