import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from etl.extract   import extract_all
from etl.transform import transform_all
from etl.load      import load_all
from etl.load_star import run_star_etl
from datetime import datetime
import logging

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR  = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

logger = logging.getLogger("etl")
logger.setLevel(logging.INFO)

if not logger.handlers:
    fh = logging.FileHandler(os.path.join(LOGS_DIR, "etl.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(sh)


def run_pipeline():
    """
    Exécuter le pipeline ETL complet:
    Extract → Transform → Load
    """
    start = datetime.now()
    logger.info("=" * 50)
    logger.info("🚀 DÉMARRAGE DU PIPELINE ETL")
    logger.info("=" * 50)

    try:
        # ============================================
        # EXTRACT
        # ============================================
        logger.info("\n📤 ÉTAPE 1: EXTRACTION")
        raw_data = extract_all()

        # ============================================
        # TRANSFORM
        # ============================================
        logger.info("\n🔄 ÉTAPE 2: TRANSFORMATION")
        transformed_data = transform_all(raw_data)

        # ============================================
        # LOAD — KPI flat tables
        # ============================================
        logger.info("\n📥 ÉTAPE 3: CHARGEMENT KPI")
        result = load_all(transformed_data)

        # ============================================
        # LOAD — Star schema (Kimball)
        # ============================================
        logger.info("\n📥 ÉTAPE 4: CHARGEMENT STAR SCHEMA")
        run_star_etl()

        # ============================================
        # RÉSUMÉ
        # ============================================
        duration = (datetime.now() - start).seconds
        logger.info("\n" + "=" * 50)
        logger.info("✅ PIPELINE ETL TERMINÉ AVEC SUCCÈS!")
        logger.info(f"⏱️  Durée: {duration} secondes")
        logger.info(f"👥 Employés traités : {len(transformed_data['employes'])}")
        logger.info(f"⏰ Pointages traités: {len(transformed_data['pointages'])}")
        logger.info(f"❌ Absences traitées: {len(transformed_data['absences'])}")
        logger.info(f"🏖️  Congés traités   : {len(transformed_data['conges'])}")
        logger.info(f"📊 KPIs calculés    : {result['kpis_employes']}")
        logger.info("=" * 50)

        return result

    except Exception as e:
        logger.error(f"❌ ERREUR PIPELINE: {e}")
        raise e


if __name__ == "__main__":
    run_pipeline()