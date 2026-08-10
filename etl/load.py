"""
ETL - Load
Chargement des données transformées dans le Data Warehouse
"""
import pandas as pd
from sqlalchemy import text
from config.database import engine
import logging

logger = logging.getLogger(__name__)

# ============================================
# Valeurs réelles dans la base de données
# ============================================
STATUT_PRESENT   = "Présent"
STATUT_EN_RETARD = "En retard"


# ============================================
# Créer les tables Data Warehouse
# ============================================

def create_dw_tables():
    """Créer les tables du Data Warehouse si elles n'existent pas"""
    logger.info("🏗️ Création des tables DW...")

    with engine.connect() as conn:
        conn.execute(text("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='DW_KPI_Employe' AND xtype='U')
            CREATE TABLE DW_KPI_Employe (
                employe_id        INT PRIMARY KEY,
                nom_complet       VARCHAR(200),
                departement       VARCHAR(100),
                poste             VARCHAR(100),
                anciennete_annees INT,
                nb_pointages      INT,
                nb_presents       INT,
                nb_retards        INT,
                nb_absences       INT,
                nb_abs_injust     INT,
                total_heures      FLOAT,
                total_retard_min  INT,
                nb_conges         INT,
                jours_conges      INT,
                taux_presence     FLOAT,
                taux_absence      FLOAT,
                taux_retard       FLOAT,
                moy_heures_jour   FLOAT,
                date_maj          DATETIME DEFAULT GETDATE()
            )
        """))

        conn.execute(text("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='DW_KPI_Mensuel' AND xtype='U')
            CREATE TABLE DW_KPI_Mensuel (
                id               INT IDENTITY(1,1) PRIMARY KEY,
                annee            INT,
                mois             INT,
                nb_presents      INT,
                nb_absences      INT,
                nb_retards       INT,
                taux_absenteisme FLOAT,
                taux_retard      FLOAT,
                total_heures     FLOAT,
                date_maj         DATETIME DEFAULT GETDATE()
            )
        """))

        conn.commit()

    logger.info("✅ Tables DW créées!")


# ============================================
# Load - Charger les données
# ============================================

def load_kpis(df_kpis: pd.DataFrame):
    """Charger les KPIs employés"""
    logger.info("📥 Chargement des KPIs employés...")

    with engine.connect() as conn:
        conn.execute(text("DELETE FROM DW_KPI_Employe"))
        conn.commit()

    # Exclure date_maj (auto-générée par SQL Server)
    cols = [c for c in df_kpis.columns if c != "date_maj"]
    df_kpis[cols].to_sql(
        "DW_KPI_Employe",
        engine,
        if_exists="append",
        index=False
    )
    logger.info(f"✅ {len(df_kpis)} KPIs employés chargés")


def load_kpis_mensuels(df_pointages: pd.DataFrame):
    """Calculer et charger les KPIs mensuels"""
    logger.info("📥 Chargement des KPIs mensuels...")

    # ✅ CORRIGÉ: utiliser les vrais statuts avec accents
    monthly = df_pointages.groupby(["annee", "mois"]).agg(
        nb_presents  = ("statut", lambda x: (x == STATUT_PRESENT).sum()),
        nb_retards   = ("statut", lambda x: (x == STATUT_EN_RETARD).sum()),
        total_heures = ("duree_travail", "sum"),
    ).reset_index()

    # nb_absences = vient de la table Absence, pas Pointage
    # On met 0 ici, Power BI utilisera directement la table Absence
    monthly["nb_absences"] = 0

    total_pointages = monthly["nb_presents"] + monthly["nb_retards"]

    monthly["taux_absenteisme"] = 0.0  # calculé séparément via table Absence

    monthly["taux_retard"] = (
        monthly["nb_retards"] / total_pointages.replace(0, 1) * 100
    ).round(2)

    monthly["total_heures"] = monthly["total_heures"].round(2)

    # ✅ Convertir en int pour éviter les erreurs de type
    monthly["nb_presents"] = monthly["nb_presents"].astype(int)
    monthly["nb_retards"]  = monthly["nb_retards"].astype(int)
    monthly["annee"]       = monthly["annee"].astype(int)
    monthly["mois"]        = monthly["mois"].astype(int)

    with engine.connect() as conn:
        conn.execute(text("DELETE FROM DW_KPI_Mensuel"))
        conn.commit()

    cols = [c for c in monthly.columns if c != "date_maj"]
    monthly[cols].to_sql(
        "DW_KPI_Mensuel",
        engine,
        if_exists="append",
        index=False
    )
    logger.info(f"✅ {len(monthly)} mois chargés")


def load_all(data: dict) -> dict:
    """Charger toutes les données transformées"""
    logger.info("🚀 Début du chargement...")

    create_dw_tables()
    load_kpis(data["kpis"])
    load_kpis_mensuels(data["pointages"])

    logger.info("✅ Chargement complet terminé!")
    return {
        "kpis_employes": len(data["kpis"]),
        "status"       : "success"
    }