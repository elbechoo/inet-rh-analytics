"""
ETL - Extract
Extraction des données depuis SQL Server
"""
import pandas as pd
from sqlalchemy import create_engine, text
from config.database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# Extract - Données RH
# ============================================

def extract_employes() -> pd.DataFrame:
    """Extraire tous les employés actifs"""
    logger.info("📤 Extraction des employés...")
    query = """
        SELECT 
            e.employe_id,
            e.matricule,
            e.nom,
            e.prenom,
            e.date_naissance,
            e.sexe,
            e.date_embauche,
            e.poste,
            e.type_contrat,
            e.statut,
            e.departement_id,
            d.nom_departement,
            DATEDIFF(YEAR, e.date_embauche, GETDATE()) as anciennete_annees
        FROM Employe e
        LEFT JOIN Departement d ON e.departement_id = d.departement_id
        WHERE e.statut = 'Actif'
    """
    df = pd.read_sql(query, engine)
    logger.info(f"✅ {len(df)} employés extraits")
    return df


def extract_pointages() -> pd.DataFrame:
    """Extraire tous les pointages"""
    logger.info("📤 Extraction des pointages...")
    query = """
        SELECT 
            p.pointage_id,
            p.employe_id,
            p.date_pointage,
            p.heure_entree,
            p.heure_sortie,
            p.duree_travail,
            p.retard_minutes,
            p.statut,
            YEAR(p.date_pointage)  as annee,
            MONTH(p.date_pointage) as mois,
            DAY(p.date_pointage)   as jour,
            DATENAME(WEEKDAY, p.date_pointage) as jour_semaine
        FROM Pointage p
        WHERE p.date_pointage IS NOT NULL
        ORDER BY p.employe_id, p.date_pointage
    """
    df = pd.read_sql(query, engine)
    logger.info(f"✅ {len(df)} pointages extraits")
    return df


def extract_absences() -> pd.DataFrame:
    """Extraire toutes les absences"""
    logger.info("📤 Extraction des absences...")
    query = """
        SELECT 
            a.absence_id,
            a.employe_id,
            a.date_absence,
            a.justifiee,
            a.statut,
            YEAR(a.date_absence)  as annee,
            MONTH(a.date_absence) as mois
        FROM Absence a
        WHERE a.date_absence IS NOT NULL
    """
    df = pd.read_sql(query, engine)
    logger.info(f"✅ {len(df)} absences extraites")
    return df


def extract_conges() -> pd.DataFrame:
    """Extraire tous les congés"""
    logger.info("📤 Extraction des congés...")
    query = """
        SELECT 
            c.conge_id,
            c.employe_id,
            c.type_conge,
            c.date_debut,
            c.date_fin,
            c.nb_jours,
            c.statut,
            YEAR(c.date_debut) as annee,
            MONTH(c.date_debut) as mois
        FROM Conge c
        WHERE c.date_debut IS NOT NULL
    """
    df = pd.read_sql(query, engine)
    logger.info(f"✅ {len(df)} congés extraits")
    return df


def extract_alertes() -> pd.DataFrame:
    """Extraire les alertes IA"""
    logger.info("📤 Extraction des alertes IA...")
    query = """
        SELECT 
            a.alerte_id,
            a.employe_id,
            a.type_alerte,
            a.niveau,
            a.message,
            a.date_alerte,
            a.est_lue,
            YEAR(a.date_alerte)  as annee,
            MONTH(a.date_alerte) as mois
        FROM AlerteIA a
    """
    df = pd.read_sql(query, engine)
    logger.info(f"✅ {len(df)} alertes extraites")
    return df


def extract_all() -> dict:
    """Extraire toutes les données"""
    logger.info("🚀 Début de l'extraction complète...")
    data = {
        "employes" : extract_employes(),
        "pointages": extract_pointages(),
        "absences" : extract_absences(),
        "conges"   : extract_conges(),
        "alertes"  : extract_alertes(),
    }
    logger.info("✅ Extraction complète terminée!")
    return data