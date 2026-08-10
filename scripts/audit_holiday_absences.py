"""Find absences that were recorded on public holidays.

Before the holiday calendar existed, absence detection only skipped weekends, so
every public holiday generated an absence for the whole workforce. Those records
inflate absence rates and are fed to the absenteeism model as real signal.

    python scripts/audit_holiday_absences.py            # report only
    python scripts/audit_holiday_absences.py --purge    # delete them

--purge deletes rows, so it prints what it will remove and asks for confirmation.
Back up the database first.
"""
import argparse
import os
import sys
from collections import Counter

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import SessionLocal
from models.models import Absence, JourFerie


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit absences falling on public holidays")
    ap.add_argument("--purge", action="store_true", help="delete the phantom absences")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        total_absences = db.query(Absence).count()

        feries = {j.date_ferie: j.nom for j in db.query(JourFerie).all()}
        if not feries:
            print("No holidays stored. Run scripts/seed_holidays.py first.")
            return

        phantom = (
            db.query(Absence)
            .filter(Absence.date_absence.in_(list(feries.keys())))
            .all()
        )

        if not phantom:
            print(f"Clean — none of your {total_absences} absences fall on a public holiday.")
            return

        by_date = Counter(a.date_absence for a in phantom)
        share = len(phantom) / total_absences * 100 if total_absences else 0

        print(f"{len(phantom)} of {total_absences} absences fall on a public holiday "
              f"({share:.1f}% of all absence records).\n")
        print("  date         employees  holiday")
        for d in sorted(by_date):
            print(f"  {d}   {by_date[d]:>6}     {feries[d]}")

        print(f"\n{len(by_date)} holidays affected.")
        print("These are not real absences — nobody was expected at work.")

        if not args.purge:
            print("\nRun again with --purge to delete them.")
            return

        if not args.yes:
            print(f"\nAbout to DELETE {len(phantom)} absence rows. Back up your database first.")
            if input("Type 'delete' to confirm: ").strip().lower() != "delete":
                print("Cancelled — nothing was changed.")
                return

        for a in phantom:
            db.delete(a)
        db.commit()
        print(f"\nDeleted {len(phantom)} phantom absences.")
        print("Re-run your AI training so the model learns from corrected data.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
