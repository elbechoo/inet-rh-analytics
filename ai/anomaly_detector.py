import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session
from ai.preprocessor import get_employe_features, get_pointagelog_dataframe
from datetime import datetime, date, timedelta

# ============================================
# Détecteur d'Anomalies
# ============================================

def detecter_anomalies_pointage(db: Session):
    """
    Détecter les anomalies dans les logs de pointage
    en utilisant Isolation Forest
    """
    df = get_pointagelog_dataframe(db)

    if df.empty or len(df) < 10:
        return detecter_anomalies_regles(db)

    # Features pour détection d'anomalies
    features = ["heure_decimal", "jour_semaine"]
    X = df[features].fillna(0)

    # Isolation Forest
    model = IsolationForest(
        contamination=0.1,  # 10% anomalies attendues
        random_state=42
    )
    df["anomalie"] = model.fit_predict(X)
    df["score"]    = model.score_samples(X)

    # -1 = anomalie, 1 = normal
    anomalies = df[df["anomalie"] == -1].copy()

    resultats = []
    for _, row in anomalies.iterrows():
        heure = row["heure_decimal"]

        # Déterminer le type d'anomalie
        if heure < 5 or heure > 22:
            type_anomalie = "Pointage hors horaires (nuit)"
            niveau = "Critique"
        elif row["jour_semaine"] >= 5:
            type_anomalie = "Pointage weekend"
            niveau = "Moyen"
        elif heure < 6:
            type_anomalie = "Pointage très tôt le matin"
            niveau = "Moyen"
        else:
            type_anomalie = "Comportement de pointage inhabituel"
            niveau = "Info"

        resultats.append({
            "employe_id"   : int(row["employe_id"]),
            "timestamp"    : str(row["timestamp"]),
            "type_anomalie": type_anomalie,
            "niveau"       : niveau,
            "heure"        : round(float(heure), 2),
            "score"        : round(float(row["score"]), 4),
        })

    return resultats


def detecter_anomalies_regles(db: Session):
    """
    Détection d'anomalies basée sur des règles métier
    """
    df = get_pointagelog_dataframe(db)

    if df.empty:
        return []

    anomalies = []

    for emp_id in df["employe_id"].unique():
        emp_logs = df[df["employe_id"] == emp_id].copy()

        for _, row in emp_logs.iterrows():
            heure = row["heure_decimal"]
            jour  = row["jour_semaine"]

            # Règle 1: Pointage la nuit (avant 5h ou après 23h)
            if heure < 5 or heure > 23:
                anomalies.append({
                    "employe_id"   : int(emp_id),
                    "timestamp"    : str(row["timestamp"]),
                    "type_anomalie": "Pointage hors horaires (nuit)",
                    "niveau"       : "Critique",
                    "heure"        : round(float(heure), 2),
                })

            # Règle 2: Pointage weekend
            elif jour >= 5:
                anomalies.append({
                    "employe_id"   : int(emp_id),
                    "timestamp"    : str(row["timestamp"]),
                    "type_anomalie": "Pointage weekend",
                    "niveau"       : "Moyen",
                    "heure"        : round(float(heure), 2),
                })

    return anomalies


def detecter_employes_sans_pointage(db: Session):
    """
    Détecter les employés qui n'ont pas pointé aujourd'hui
    """
    from models.models import Employe, Pointage

    today    = date.today()
    employes = db.query(Employe).filter(Employe.statut == "Actif").all()

    pointages_today = db.query(Pointage).filter(
        Pointage.date_pointage == today
    ).all()

    emp_pointe = {p.employe_id for p in pointages_today}

    sans_pointage = []
    for emp in employes:
        if emp.employe_id not in emp_pointe:
            sans_pointage.append({
                "employe_id": emp.employe_id,
                "nom"       : f"{emp.prenom} {emp.nom}",
                "matricule" : emp.matricule,
                "message"   : "Aucun pointage détecté aujourd'hui",
                "niveau"    : "Critique"
            })

    return sans_pointage


def detecter_retards_frequents(db: Session, seuil: int = 3):
    """
    Détecter les employés avec retards fréquents ce mois
    """
    from models.models import Pointage

    debut_mois = date.today().replace(day=1)

    pointages = db.query(Pointage).filter(
        Pointage.date_pointage >= debut_mois,
        Pointage.statut == "En retard"
    ).all()

    # Compter retards par employé
    retards = {}
    for p in pointages:
        retards[p.employe_id] = retards.get(p.employe_id, 0) + 1

    resultats = []
    for emp_id, nb in retards.items():
        if nb >= seuil:
            from models.models import Employe
            emp = db.query(Employe).filter(
                Employe.employe_id == emp_id
            ).first()
            if emp:
                resultats.append({
                    "employe_id" : emp_id,
                    "nom"        : f"{emp.prenom} {emp.nom}",
                    "nb_retards" : nb,
                    "niveau"     : "Critique" if nb >= 5 else "Moyen",
                    "message"    : f"{nb} retards ce mois"
                })

    return sorted(resultats, key=lambda x: x["nb_retards"], reverse=True)