"""
iNET RH — Historical Data Seeder
Backfills realistic attendance, absence, and leave data.
Fully idempotent — skips dates that already have pointage records.

Usage:
    python scripts/seed_history.py                     # default: 365 days
    python scripts/seed_history.py --start-year 2016   # 2016-01-01 to today
    python scripts/seed_history.py --days 180          # last 6 months
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
from datetime import date, timedelta

from config.database import SessionLocal
from demo.simulate_day import simulate_day_entrees, simulate_day_sorties

# logs/ is gitignored and excluded from the container image, so it will not
# exist on a fresh clone or in Docker. Create it rather than crashing, and fall
# back to console-only if the location is not writable.
_handlers = [logging.StreamHandler()]
try:
    os.makedirs("logs", exist_ok=True)
    _handlers.append(logging.FileHandler("logs/seed_history.log", encoding="utf-8"))
except OSError:
    pass

logging.basicConfig(
    level    = logging.INFO,
    format   = "%(asctime)s - %(levelname)s - %(message)s",
    handlers = _handlers,
)
logger = logging.getLogger(__name__)


def seed_history(start: date) -> None:
    today = date.today()

    if start >= today:
        logger.error(f"Start date {start} must be before today {today}")
        return

    total_calendar = (today - start).days
    total_workdays_estimated = int(total_calendar * 5 / 7)

    logger.info("=" * 60)
    logger.info("iNET RH — HISTORICAL DATA SEEDER")
    logger.info(f"Period    : {start} → {today - timedelta(days=1)}")
    logger.info(f"Calendar  : {total_calendar} days (~{total_workdays_estimated} workdays)")
    logger.info("=" * 60)

    db = SessionLocal()
    try:
        total_workdays = 0
        total_presents = total_retards = total_absents = 0
        total_sorties  = total_conges  = 0

        current = start
        while current < today:
            if current.weekday() >= 5:
                current += timedelta(days=1)
                continue

            e = simulate_day_entrees(db, current)
            s = simulate_day_sorties(db, current)

            if "skipped" not in e:
                total_presents += e.get("presents", 0)
                total_retards  += e.get("retards",  0)
                total_absents  += e.get("absents",  0)
                total_sorties  += s.get("sorties",  0)
                total_conges   += s.get("conges",   0)
                total_workdays += 1

            # Progress every 60 workdays (~3 months)
            if total_workdays > 0 and total_workdays % 60 == 0:
                pct = int(total_workdays / total_workdays_estimated * 100)
                logger.info(f"  [{pct:3d}%] {current}  —  {total_workdays} workdays done")

            current += timedelta(days=1)

        logger.info("=" * 60)
        logger.info("SEED COMPLETE")
        logger.info(f"  Workdays seeded  : {total_workdays}")
        logger.info(f"  Present records  : {total_presents}")
        logger.info(f"  Late records     : {total_retards}")
        logger.info(f"  Absence records  : {total_absents}")
        logger.info(f"  Normal exits     : {total_sorties}")
        logger.info(f"  Leave requests   : {total_conges}")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.info("Seeder interrupted — partial data already committed to DB.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed historical HR data")

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--start-year", type=int, metavar="YEAR",
        help="Seed from January 1st of this year to today (e.g. --start-year 2016)"
    )
    group.add_argument(
        "--days", type=int,
        help="Seed last N calendar days (e.g. --days 365)"
    )

    args = parser.parse_args()

    if args.start_year:
        start_date = date(args.start_year, 1, 1)
    elif args.days:
        start_date = date.today() - timedelta(days=args.days)
    else:
        start_date = date.today() - timedelta(days=365)

    seed_history(start_date)
