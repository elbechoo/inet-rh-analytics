"""Seed the public-holiday calendar.

    python scripts/seed_holidays.py                    # current year -> +2
    python scripts/seed_holidays.py --from 2024 --to 2028
    python scripts/seed_holidays.py --overwrite        # reset names/types
    python scripts/seed_holidays.py --list             # show what is stored

Islamic dates are official announcements where known and estimates beyond that.
Confirm each year with the Journal Officiel and correct any date that differs —
re-running without --overwrite will not undo your corrections.
"""
import argparse
import os
import sys
from datetime import date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import SessionLocal, engine, Base
from models.models import JourFerie
from services.holiday_service import seed


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed Tunisian public holidays")
    ap.add_argument("--from", dest="y_from", type=int, default=date.today().year)
    ap.add_argument("--to", dest="y_to", type=int, default=date.today().year + 2)
    ap.add_argument("--overwrite", action="store_true", help="refresh existing entries")
    ap.add_argument("--list", action="store_true", help="print stored holidays and exit")
    args = ap.parse_args()

    # The JourFerie table is new, and this script may run before the API has
    # ever booted. create_all only adds what is missing — existing tables and
    # their data are untouched.
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if args.list:
            rows = db.query(JourFerie).order_by(JourFerie.date_ferie).all()
            if not rows:
                print("no holidays stored — run without --list to seed")
                return
            print(f"{len(rows)} holidays stored:\n")
            current_year = None
            for r in rows:
                if r.date_ferie.year != current_year:
                    current_year = r.date_ferie.year
                    print(f"  {current_year}")
                flag = "" if r.chome else "  (worked)"
                print(f"    {r.date_ferie}  {r.nom:<42} {r.type_ferie}{flag}")
            return

        res = seed(db, args.y_from, args.y_to, overwrite=args.overwrite)
        print(f"holidays {args.y_from}–{args.y_to}: "
              f"{res['created']} created, {res['updated']} updated, {res['skipped']} left as-is")
        print("\nLeave deduction and absence detection now skip these dates.")
        print("Confirm the Islamic dates each year — they are set by moon sighting.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
