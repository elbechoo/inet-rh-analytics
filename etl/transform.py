"""
ETL - Transform
Nettoyage et transformation des données RH
"""
import pandas as pd
import numpy as np
from datetime import date
import logging

logger = logging.getLogger(__name__)

# ============================================
# Valeurs réelles dans la base de données
# ============================================
STATUT_PRESENT   = "Présent"          # ✅ avec accent
STATUT_EN_RETARD = "En retard"
STATUT_SORTIE    = "Sortie manquante" # ou "Sortie man..."


# ============================================
# Transform - Nettoyage et enrichissement
# ============================================

def transform_employes(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoyer et enrichir les données employés"""
    logger.info("🔄 Transformation des employés...")

    df["nom"]    = df["nom"].str.strip().str.upper()
    df["prenom"] = df["prenom"].str.strip().str.title()
    df["nom_complet"] = df["prenom"] + " " + df["nom"]

    today = pd.Timestamp.now()
    df["date_naissance"] = pd.to_datetime(df["date_naissance"], errors="coerce")
    df["age"] = ((today - df["date_naissance"]).dt.days / 365).round(0).astype("Int64")

    df["categorie_anciennete"] = pd.cut(
        df["anciennete_annees"],
        bins   = [-1, 1, 3, 5, 10, 100],
        labels = ["< 1 an", "1-3 ans", "3-5 ans", "5-10 ans", "> 10 ans"]
    )

    df["tranche_age"] = pd.cut(
        df["age"],
        bins   = [0, 25, 35, 45, 55, 100],
        labels = ["< 25", "25-35", "35-45", "45-55", "> 55"]
    )

    logger.info(f"✅ {len(df)} employés transformés")
    return df


def transform_pointages(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoyer et enrichir les pointages"""
    logger.info("🔄 Transformation des pointages...")

    df["duree_travail"]  = df["duree_travail"].fillna(0)
    df["retard_minutes"] = df["retard_minutes"].fillna(0)
    df["statut"]         = df["statut"].fillna("Inconnu")

    # ✅ Normaliser les statuts (strip espaces + accents cohérents)
    df["statut"] = df["statut"].str.strip()

    df["categorie_retard"] = pd.cut(
        df["retard_minutes"],
        bins   = [-1, 0, 15, 30, 60, 10000],
        labels = ["À l'heure", "Léger (< 15min)", "Moyen (15-30min)",
                  "Important (30-60min)", "Très important (> 1h)"]
    )

    df["est_weekend"] = df["jour_semaine"].isin(["Saturday", "Sunday", "samedi", "dimanche"])
    df["date_pointage"] = pd.to_datetime(df["date_pointage"])

    logger.info(f"✅ {len(df)} pointages transformés")
    return df


def transform_absences(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoyer les absences"""
    logger.info("🔄 Transformation des absences...")

    df["justifiee"]    = df["justifiee"].fillna(False).astype(bool)
    df["statut"]       = df["statut"].fillna("Non justifiée")
    df["date_absence"] = pd.to_datetime(df["date_absence"])

    logger.info(f"✅ {len(df)} absences transformées")
    return df


def transform_conges(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoyer les congés"""
    logger.info("🔄 Transformation des congés...")

    df["nb_jours"]   = df["nb_jours"].fillna(0).astype(int)
    df["statut"]     = df["statut"].fillna("En attente")
    df["type_conge"] = df["type_conge"].fillna("Autre")

    logger.info(f"✅ {len(df)} congés transformés")
    return df


def calculate_kpis(employes: pd.DataFrame,
                   pointages: pd.DataFrame,
                   absences: pd.DataFrame,
                   conges: pd.DataFrame) -> pd.DataFrame:
    """
    Calculer les KPIs par employé
    """
    logger.info("📊 Calcul des KPIs...")

    # ✅ Debug: afficher les valeurs uniques de statut
    statuts_uniques = pointages["statut"].unique()
    logger.info(f"🔍 Statuts pointage trouvés: {statuts_uniques}")

    kpis = []

    for emp_id in employes["employe_id"]:
        emp = employes[employes["employe_id"] == emp_id].iloc[0]
        p   = pointages[pointages["employe_id"] == emp_id]
        a   = absences[absences["employe_id"] == emp_id]
        c   = conges[conges["employe_id"] == emp_id]

        nb_pointages     = len(p)

        # ✅ CORRIGÉ: utiliser les vrais statuts de la DB
        nb_presents      = len(p[p["statut"] == STATUT_PRESENT])
        nb_retards       = len(p[p["statut"] == STATUT_EN_RETARD])
        # Tout ce qui n'est ni Présent ni En retard = problème de sortie
        nb_autres        = nb_pointages - nb_presents - nb_retards

        nb_absences      = len(a)
        nb_abs_injust    = len(a[a["justifiee"] == False])
        total_heures     = p["duree_travail"].sum()
        total_retard_min = p["retard_minutes"].sum()

        # ✅ CORRIGÉ: statut congé avec accent
        nb_conges    = len(c[c["statut"] == "Approuvé"])
        jours_conges = c[c["statut"] == "Approuvé"]["nb_jours"].sum()

        # ✅ Calculs KPI corrects
        taux_presence = (nb_presents / nb_pointages * 100) if nb_pointages > 0 else 0
        taux_absence  = (nb_absences / max(nb_pointages + nb_absences, 1) * 100)
        taux_retard   = (nb_retards  / nb_pointages * 100) if nb_pointages > 0 else 0
        moy_heures    = (total_heures / nb_pointages) if nb_pointages > 0 else 0

        nom_complet = emp.get("nom_complet", f"{emp['prenom']} {emp['nom']}")

        kpis.append({
            "employe_id"       : int(emp_id),
            "nom_complet"      : nom_complet,
            "departement"      : emp["nom_departement"],
            "poste"            : emp["poste"],
            "anciennete_annees": int(emp["anciennete_annees"]),
            "nb_pointages"     : int(nb_pointages),
            "nb_presents"      : int(nb_presents),
            "nb_retards"       : int(nb_retards),
            "nb_absences"      : int(nb_absences),
            "nb_abs_injust"    : int(nb_abs_injust),
            "total_heures"     : round(float(total_heures), 2),
            "total_retard_min" : int(total_retard_min),
            "nb_conges"        : int(nb_conges),
            "jours_conges"     : int(jours_conges),
            "taux_presence"    : round(taux_presence, 2),
            "taux_absence"     : round(taux_absence, 2),
            "taux_retard"      : round(taux_retard, 2),
            "moy_heures_jour"  : round(float(moy_heures), 2),
        })

    df_kpis = pd.DataFrame(kpis)
    logger.info(f"✅ KPIs calculés pour {len(df_kpis)} employés")

    # ✅ Debug: afficher un sample des KPIs
    logger.info(f"📊 Sample KPIs:\n{df_kpis[['nom_complet','nb_pointages','nb_presents','taux_presence']].head()}")

    return df_kpis


def transform_all(data: dict) -> dict:
    """Transformer toutes les données"""
    logger.info("🚀 Début de la transformation complète...")

    employes  = transform_employes(data["employes"])
    pointages = transform_pointages(data["pointages"])
    absences  = transform_absences(data["absences"])
    conges    = transform_conges(data["conges"])
    kpis      = calculate_kpis(employes, pointages, absences, conges)

    result = {
        "employes" : employes,
        "pointages": pointages,
        "absences" : absences,
        "conges"   : conges,
        "alertes"  : data["alertes"],
        "kpis"     : kpis,
    }

    logger.info("✅ Transformation complète terminée!")
    return result