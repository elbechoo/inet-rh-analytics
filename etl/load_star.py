"""
ETL — Star Schema Loader (Kimball methodology)
Populates: Dim_Date, Dim_Departement, Dim_Employe,
           Fact_Pointage, Fact_Absence, Fact_Conge
"""
import pandas as pd
from datetime import date, timedelta
from sqlalchemy import text
from config.database import engine
import logging

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────

def _date_id(d: date) -> int:
    return int(d.strftime("%Y%m%d"))


def _saison(mois: int) -> str:
    if mois in (12, 1, 2):  return "Hiver"
    if mois in (3, 4, 5):   return "Printemps"
    if mois in (6, 7, 8):   return "Été"
    return "Automne"


NOMS_MOIS = ["Janvier","Février","Mars","Avril","Mai","Juin",
             "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
NOMS_JOUR = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]


# ──────────────────────────────────────────────
# Dim_Date
# ──────────────────────────────────────────────

def load_dim_date(annee_debut: int = 2015, annee_fin: int = 2027):
    logger.info("Dim_Date — generating calendar rows...")

    rows = []
    current = date(annee_debut, 1, 1)
    end     = date(annee_fin, 12, 31)
    while current <= end:
        iso_cal = current.isocalendar()
        rows.append({
            "date_id"        : _date_id(current),
            "date_complete"  : current,
            "annee"          : current.year,
            "trimestre"      : (current.month - 1) // 3 + 1,
            "mois"           : current.month,
            "nom_mois"       : NOMS_MOIS[current.month - 1],
            "semaine"        : iso_cal[1],
            "jour"           : current.day,
            "nom_jour"       : NOMS_JOUR[current.weekday()],
            "jour_semaine_num": current.weekday(),
            "est_weekend"    : 1 if current.weekday() >= 5 else 0,
            "saison"         : _saison(current.month),
        })
        current += timedelta(days=1)

    df = pd.DataFrame(rows)

    with engine.connect() as conn:
        existing = conn.execute(text("SELECT COUNT(*) FROM Dim_Date")).scalar()
        if existing == len(rows):
            logger.info(f"Dim_Date already up-to-date ({existing} rows). Skipping.")
            return
        conn.execute(text("DELETE FROM Dim_Date"))
        conn.commit()

    df.to_sql("Dim_Date", engine, if_exists="append", index=False)
    logger.info(f"Dim_Date — {len(df)} rows loaded.")


# ──────────────────────────────────────────────
# Dim_Departement
# ──────────────────────────────────────────────

def load_dim_departement():
    logger.info("Dim_Departement — loading...")

    query = """
        SELECT departement_id,
               nom_departement,
               sous_departement
        FROM   Departement
    """
    df = pd.read_sql(query, engine)
    df["date_chargement"] = pd.Timestamp.now()

    with engine.connect() as conn:
        # Order matters: facts must be cleared before the dimensions they reference.
        for stmt in (
            "IF OBJECT_ID('Fact_Formation','U') IS NOT NULL DELETE FROM Fact_Formation",
            "DELETE FROM Fact_Conge",
            "DELETE FROM Fact_Absence",
            "DELETE FROM Fact_Pointage",
            "IF OBJECT_ID('Dim_Formation','U') IS NOT NULL DELETE FROM Dim_Formation",
            "DELETE FROM Dim_Departement",
            "DELETE FROM Dim_Employe",
        ):
            conn.execute(text(stmt))
        conn.commit()

    df.to_sql("Dim_Departement", engine, if_exists="append", index=False)
    logger.info(f"Dim_Departement — {len(df)} rows loaded.")


# ──────────────────────────────────────────────
# Dim_Employe
# ──────────────────────────────────────────────

def load_dim_employe():
    logger.info("Dim_Employe — loading...")

    query = """
        SELECT e.employe_id,
               e.matricule,
               CONCAT(e.prenom, ' ', e.nom)              AS nom_complet,
               e.poste,
               e.type_contrat,
               e.date_embauche,
               DATEDIFF(YEAR, e.date_embauche, GETDATE()) AS anciennete_annees,
               d.departement_id,
               d.nom_departement,
               d.sous_departement
        FROM   Employe     e
        JOIN   Departement d ON e.departement_id = d.departement_id
    """
    df = pd.read_sql(query, engine)
    df["date_chargement"] = pd.Timestamp.now()

    df.to_sql("Dim_Employe", engine, if_exists="append", index=False)
    logger.info(f"Dim_Employe — {len(df)} rows loaded.")


# ──────────────────────────────────────────────
# Fact_Pointage
# ──────────────────────────────────────────────

def load_fact_pointage():
    logger.info("Fact_Pointage — loading...")

    query = """
        SELECT p.pointage_id,
               p.employe_id,
               p.date_pointage,
               p.heure_entree,
               p.duree_travail,
               p.retard_minutes,
               p.statut,
               de.employe_sk,
               dd.departement_sk
        FROM   Pointage    p
        JOIN   Employe     e  ON p.employe_id    = e.employe_id
        JOIN   Dim_Employe de ON de.employe_id   = e.employe_id
        JOIN   Dim_Departement dd ON dd.departement_id = e.departement_id
        WHERE  p.date_pointage IS NOT NULL
    """
    df = pd.read_sql(query, engine)

    df["date_id"] = df["date_pointage"].apply(lambda d: _date_id(d) if d else None)

    # Compute heure_entree_decimal for Power BI time-of-day analysis
    def to_decimal(t):
        if pd.isnull(t):
            return None
        if hasattr(t, "hour"):
            return round(t.hour + t.minute / 60, 4)
        return None

    df["heure_entree_decimal"] = df["heure_entree"].apply(to_decimal)

    df["est_present"]      = (df["statut"] == "Présent").astype(int)
    df["est_retard"]       = (df["statut"] == "En retard").astype(int)
    df["sortie_manquante"] = (df["statut"] == "Sortie manquante").astype(int)

    cols = [
        "date_id", "employe_sk", "departement_sk", "pointage_id",
        "statut", "heure_entree_decimal", "duree_travail", "retard_minutes",
        "est_present", "est_retard", "sortie_manquante",
    ]
    df[cols].to_sql("Fact_Pointage", engine, if_exists="append", index=False)
    logger.info(f"Fact_Pointage — {len(df)} rows loaded.")


# ──────────────────────────────────────────────
# Fact_Absence
# ──────────────────────────────────────────────

def load_fact_absence():
    logger.info("Fact_Absence — loading...")

    query = """
        SELECT a.absence_id,
               a.employe_id,
               a.date_absence,
               a.justifiee     AS est_justifiee,
               a.motif,
               de.employe_sk,
               dd.departement_sk
        FROM   Absence     a
        JOIN   Employe     e  ON a.employe_id    = e.employe_id
        JOIN   Dim_Employe de ON de.employe_id   = e.employe_id
        JOIN   Dim_Departement dd ON dd.departement_id = e.departement_id
        WHERE  a.date_absence IS NOT NULL
    """
    df = pd.read_sql(query, engine)

    df["date_id"]     = df["date_absence"].apply(lambda d: _date_id(d) if d else None)
    df["nb_absences"] = 1

    cols = [
        "date_id", "employe_sk", "departement_sk", "absence_id",
        "motif", "est_justifiee", "nb_absences",
    ]
    df[cols].to_sql("Fact_Absence", engine, if_exists="append", index=False)
    logger.info(f"Fact_Absence — {len(df)} rows loaded.")


# ──────────────────────────────────────────────
# Fact_Conge
# ──────────────────────────────────────────────

def load_fact_conge():
    logger.info("Fact_Conge — loading...")

    query = """
        SELECT c.conge_id,
               c.employe_id,
               c.date_debut,
               c.date_fin,
               c.type_conge,
               c.statut,
               c.nb_jours,
               de.employe_sk,
               dd.departement_sk
        FROM   Conge       c
        JOIN   Employe     e  ON c.employe_id    = e.employe_id
        JOIN   Dim_Employe de ON de.employe_id   = e.employe_id
        JOIN   Dim_Departement dd ON dd.departement_id = e.departement_id
        WHERE  c.date_debut IS NOT NULL
    """
    df = pd.read_sql(query, engine)

    df["date_debut_id"] = df["date_debut"].apply(lambda d: _date_id(d) if d else None)
    df["date_fin_id"]   = df["date_fin"].apply(lambda d: _date_id(d) if d else None)

    cols = [
        "date_debut_id", "date_fin_id", "employe_sk", "departement_sk",
        "conge_id", "type_conge", "statut", "nb_jours",
    ]
    df[cols].to_sql("Fact_Conge", engine, if_exists="append", index=False)
    logger.info(f"Fact_Conge — {len(df)} rows loaded.")


# ──────────────────────────────────────────────
# Dim_Formation
# ──────────────────────────────────────────────

def load_dim_formation():
    logger.info("Dim_Formation — loading...")

    query = """
        SELECT formation_id,
               titre,
               organisateur,
               type_formation,
               date_debut,
               date_fin,
               DATEDIFF(DAY, date_debut, date_fin) + 1 AS duree_jours
        FROM   Formation
    """
    df = pd.read_sql(query, engine)
    df["date_chargement"] = pd.Timestamp.now()

    df.to_sql("Dim_Formation", engine, if_exists="append", index=False)
    logger.info(f"Dim_Formation — {len(df)} rows loaded.")


# ──────────────────────────────────────────────
# Fact_Formation
# Grain: 1 row per employee per training participation.
# The date dimension is driven by the formation start date.
# ──────────────────────────────────────────────

def load_fact_formation():
    logger.info("Fact_Formation — loading...")

    query = """
        SELECT pf.presence_id,
               pf.formation_id,
               pf.employe_id,
               pf.presence,
               pf.score,
               f.date_debut,
               de.employe_sk,
               dd.departement_sk,
               df.formation_sk
        FROM   PresenceFormation pf
        JOIN   Formation         f  ON pf.formation_id = f.formation_id
        JOIN   Employe           e  ON pf.employe_id   = e.employe_id
        JOIN   Dim_Employe       de ON de.employe_id   = e.employe_id
        JOIN   Dim_Departement   dd ON dd.departement_id = e.departement_id
        JOIN   Dim_Formation     df ON df.formation_id = pf.formation_id
        WHERE  f.date_debut IS NOT NULL
    """
    df = pd.read_sql(query, engine)

    df["date_id"] = df["date_debut"].apply(lambda d: _date_id(d) if d else None)
    df["est_present"] = df["presence"].fillna(False).astype(int)
    df["nb_participations"] = 1

    cols = [
        "date_id", "employe_sk", "departement_sk", "formation_sk",
        "presence_id", "est_present", "score", "nb_participations",
    ]
    df[cols].to_sql("Fact_Formation", engine, if_exists="append", index=False)
    logger.info(f"Fact_Formation — {len(df)} rows loaded.")


# ──────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────

def run_star_etl():
    """Full star schema refresh — idempotent, safe to re-run."""
    logger.info("=" * 50)
    logger.info("STAR SCHEMA ETL — START")
    logger.info("=" * 50)

    load_dim_date()
    load_dim_departement()   # also truncates every fact + Dim_Employe + Dim_Formation first
    load_dim_employe()
    load_dim_formation()
    load_fact_pointage()
    load_fact_absence()
    load_fact_conge()
    load_fact_formation()

    logger.info("=" * 50)
    logger.info("STAR SCHEMA ETL — COMPLETE")
    logger.info("=" * 50)


if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_star_etl()
