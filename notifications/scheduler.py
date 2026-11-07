"""
iNET RH - Scheduler
Planification complète:
  07:00 -> Simulation Entrées
  18:00 -> Simulation Sorties + Congés (end-of-day)
  23:00 -> ETL Pipeline
  00:00 -> Email Digest
  Dimanche 02:00 -> Auto Retraining Modèle IA
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from notifications.digest_builder import get_daily_data, build_html_digest, build_and_get_subject
from notifications.email_sender import send_email
from datetime import datetime
import logging

# logs/ is gitignored and not present in the container image, so it will not
# exist on a fresh clone or deployment. Create it rather than crashing at
# import time, and fall back to console-only if it is not writable - a
# read-only filesystem must not stop the scheduler from running.
_handlers = [logging.StreamHandler()]
try:
    os.makedirs("logs", exist_ok=True)
    _handlers.insert(0, logging.FileHandler("logs/scheduler.log", encoding="utf-8"))
except OSError:
    pass

logging.basicConfig(
    level    = logging.INFO,
    format   = "%(asctime)s - %(levelname)s - %(message)s",
    handlers = _handlers,
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# JOB 1 - SIMULATION ENTRÉES (07:00)
# ─────────────────────────────────────────
def job_simulate_entrees():
    logger.info("=" * 50)
    logger.info(f"📍 JOB: Simulation Entrées - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    logger.info("=" * 50)
    try:
        from demo.simulate_day import simulate_entrees
        simulate_entrees()
        logger.info("✅ Simulation entrées terminée!")
    except Exception as e:
        logger.error(f"❌ Erreur simulation entrées: {e}")


# ─────────────────────────────────────────
# JOB 2 - SIMULATION SORTIES + CONGÉS (17:00)
# ─────────────────────────────────────────
def job_simulate_sorties():
    logger.info("=" * 50)
    logger.info(f"📍 JOB: Simulation Sorties + Congés - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    logger.info("=" * 50)
    try:
        from demo.simulate_day import simulate_sorties_et_conges
        simulate_sorties_et_conges()
        logger.info("✅ Simulation sorties terminée!")
    except Exception as e:
        logger.error(f"❌ Erreur simulation sorties: {e}")


# ─────────────────────────────────────────
# JOB 3 - ETL PIPELINE (23:00)
# ─────────────────────────────────────────
def job_run_etl():
    logger.info("=" * 50)
    logger.info(f"⚙️  JOB: ETL Pipeline - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    logger.info("=" * 50)
    start = datetime.now()
    try:
        from etl.pipeline import run_pipeline
        run_pipeline()
        duration = (datetime.now() - start).seconds
        logger.info(f"✅ ETL terminé! Durée: {duration}s")
    except Exception as e:
        logger.error(f"❌ Erreur ETL: {e}")
        try:
            send_email(
                subject   = "🔴 iNET RH - ERREUR ETL Pipeline",
                html_body = f"""
                <h2>❌ Le pipeline ETL a échoué</h2>
                <p><b>Date:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                <p><b>Erreur:</b> {str(e)}</p>
                <p>Veuillez vérifier les logs et relancer manuellement.</p>
                """
            )
        except Exception:
            pass


# ─────────────────────────────────────────
# JOB 4 - AUTO RETRAINING (Dimanche 02:00)
# ─────────────────────────────────────────
def job_retrain_model():
    logger.info("=" * 50)
    logger.info(f"🤖 JOB: Auto Retraining - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    logger.info("=" * 50)

    try:
        from config.database import SessionLocal
        from ai.absenteeism_model import entrainer_modele
        import pickle
        import os

        db = SessionLocal()

        # Lire accuracy ancien modèle si existe
        old_accuracy = None
        SCALER_PATH  = "ai/models/scaler.pkl"
        MODEL_PATH   = "ai/models/absenteeism_model.pkl"

        if os.path.exists(MODEL_PATH):
            try:
                # On garde juste la trace - pas besoin de recharger
                logger.info("📦 Ancien modèle détecté - sera remplacé")
                old_accuracy = "inconnu"
            except Exception:
                pass

        # Réentraîner
        logger.info("🔄 Réentraînement en cours...")
        result = entrainer_modele(db)

        # v2 (deterioration model) - trained here so predictions never retrain
        # on a user request. Failures are logged but must not break the legacy job.
        try:
            from ai.risk_model import train_risk_model
            v2 = train_risk_model(db)
            if v2.get("status") == "success":
                logger.info(
                    "✅ v2 retrained - F1 %.1f vs baseline %.1f (uplift %+.1f) on %d rows",
                    v2.get("f1", 0), v2.get("baseline_f1", 0),
                    v2.get("uplift_f1", 0), v2.get("n_rows_total", 0),
                )
                if not v2.get("beats_baseline"):
                    logger.warning("⚠️  v2 does NOT beat the rule-based baseline - review features/target")
            else:
                logger.warning("⚠️  v2 retraining skipped: %s", v2.get("error"))
        except Exception as e:
            logger.warning("⚠️  v2 retraining error: %s", e)

        db.close()

        if "error" in result:
            logger.error(f"❌ Erreur retraining: {result['error']}")
            send_email(
                subject   = "🔴 iNET RH - Erreur Retraining Modèle IA",
                html_body = f"""
                <h2>❌ Le réentraînement a échoué</h2>
                <p><b>Date:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                <p><b>Erreur:</b> {result['error']}</p>
                """
            )
            return

        new_accuracy  = result["accuracy"]
        nb_employes   = result["nb_employes"]
        nb_a_risque   = result["nb_a_risque"]

        logger.info(f"✅ Modèle réentraîné!")
        logger.info(f"   🎯 Accuracy   : {new_accuracy}%")
        logger.info(f"   👥 Employés   : {nb_employes}")
        logger.info(f"   ⚠️  À risque   : {nb_a_risque}")

        # Email de confirmation
        send_email(
            subject   = f"🤖 iNET RH - Modèle IA Réentraîné | Accuracy: {new_accuracy}%",
            html_body = f"""
            <h2>🤖 Réentraînement Automatique - Modèle Absentéisme</h2>
            <p><b>Date:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            <hr>
            <table style="border-collapse:collapse; width:100%">
              <tr style="background:#f0f0f0">
                <td style="padding:8px"><b>🎯 Accuracy</b></td>
                <td style="padding:8px">{new_accuracy}%</td>
              </tr>
              <tr>
                <td style="padding:8px"><b>👥 Employés traités</b></td>
                <td style="padding:8px">{nb_employes}</td>
              </tr>
              <tr style="background:#f0f0f0">
                <td style="padding:8px"><b>⚠️ Employés à risque</b></td>
                <td style="padding:8px">{nb_a_risque}</td>
              </tr>
            </table>
            <p style="color:green">✅ Nouveau modèle sauvegardé avec succès.</p>
            """
        )

    except Exception as e:
        logger.error(f"❌ Erreur retraining: {e}")


# ─────────────────────────────────────────
# JOB 5 - EMAIL DIGEST (00:00)
# ─────────────────────────────────────────
def job_send_email():
    logger.info("=" * 50)
    logger.info(f"📧 JOB: Email Digest - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    logger.info("=" * 50)
    try:
        data    = get_daily_data()
        html    = build_html_digest(data)
        subject = build_and_get_subject(data)

        nb_alertes  = len(data["alertes"])
        nb_conges   = len(data["conges"])
        nb_absences = len(data["absences_today"])
        logger.info(f"   -> {nb_alertes} alertes, {nb_conges} congés, {nb_absences} absences")

        success = send_email(subject=subject, html_body=html)
        if success:
            logger.info("✅ Email envoyé avec succès!")
        else:
            logger.error("❌ Échec envoi email")
    except Exception as e:
        logger.error(f"❌ Erreur email: {e}")


# ─────────────────────────────────────────
# SCHEDULER
# ─────────────────────────────────────────
def run_scheduler():
    scheduler = BlockingScheduler(timezone="Africa/Tunis")

    # 07:00 - Entrées
    scheduler.add_job(
        func    = job_simulate_entrees,
        trigger = CronTrigger(hour=7, minute=0),
        id      = "simulate_entrees",
        name    = "Simulation Entrées",
        replace_existing = True,
    )

    # 18:00 - Sorties + Congés (end-of-day)
    scheduler.add_job(
        func    = job_simulate_sorties,
        trigger = CronTrigger(hour=18, minute=0),
        id      = "simulate_sorties",
        name    = "Simulation Sorties + Congés",
        replace_existing = True,
    )

    # 23:00 - ETL
    scheduler.add_job(
        func    = job_run_etl,
        trigger = CronTrigger(hour=23, minute=0),
        id      = "etl_pipeline",
        name    = "ETL Pipeline",
        replace_existing = True,
    )

    # Dimanche 02:00 - Retraining
    scheduler.add_job(
        func    = job_retrain_model,
        trigger = CronTrigger(day_of_week="sun", hour=2, minute=0),
        id      = "auto_retrain",
        name    = "Auto Retraining Modèle IA",
        replace_existing = True,
    )

    # 00:00 - Email
    scheduler.add_job(
        func    = job_send_email,
        trigger = CronTrigger(hour=0, minute=0),
        id      = "daily_digest",
        name    = "Email Digest",
        replace_existing = True,
    )

    logger.info("Scheduler started:")
    logger.info("   Simulation Entries  -> Mon-Fri 07:00")
    logger.info("   Simulation Exits    -> Mon-Fri 18:00")
    logger.info("   ETL Pipeline        -> 23:00")
    logger.info("   Auto Retraining     -> Sunday 02:00")
    logger.info("   Email Digest        -> 00:00")
    logger.info("   Press Ctrl+C to stop")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("⏹️  Scheduler arrêté")
        scheduler.shutdown()


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="iNET RH - Scheduler Complet")
    parser.add_argument("--now-entrees", action="store_true", help="Simulate entries now")
    parser.add_argument("--now-sorties", action="store_true", help="Simulate exits now")
    parser.add_argument("--now-all-sim", action="store_true", help="Simulate entries + exits now")
    parser.add_argument("--now-etl",     action="store_true", help="Run ETL pipeline now")
    parser.add_argument("--now-email",   action="store_true", help="Send email digest now")
    parser.add_argument("--now-retrain", action="store_true", help="Retrain AI model now")
    parser.add_argument("--now-seed",    action="store_true", help="Seed 1 year of historical data now")
    parser.add_argument("--seed-days",   type=int, default=365, help="Days to backfill with --now-seed (default: 365)")
    parser.add_argument("--now-all",     action="store_true", help="Run everything now")
    args = parser.parse_args()

    if args.now_entrees:
        logger.info("Test mode - Entries")
        job_simulate_entrees()
    elif args.now_sorties:
        logger.info("Test mode - Exits")
        job_simulate_sorties()
    elif args.now_all_sim:
        logger.info("Test mode - Entries + Exits")
        job_simulate_entrees()
        job_simulate_sorties()
    elif args.now_etl:
        logger.info("Test mode - ETL")
        job_run_etl()
    elif args.now_email:
        logger.info("Test mode - Email")
        job_send_email()
    elif args.now_retrain:
        logger.info("Test mode - Retraining")
        job_retrain_model()
    elif args.now_seed:
        logger.info(f"Test mode - Seeding {args.seed_days} days of history")
        from scripts.seed_history import seed_history
        seed_history(args.seed_days)
    elif args.now_all:
        logger.info("Test mode - ALL")
        job_simulate_entrees()
        job_simulate_sorties()
        job_run_etl()
        job_retrain_model()
        job_send_email()
    else:
        run_scheduler()