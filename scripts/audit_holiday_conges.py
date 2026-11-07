"""Find leave requests over-charged because they span a public holiday.

Before the holiday calendar existed, nb_jours excluded weekends but not holidays,
so an employee whose leave covered Aïd paid for those days out of their own
balance. Fixing the calculation does not correct records already stored.

This measures ONLY the holiday effect: it counts each request under the old rule
(weekends only) and the new rule (weekends + holidays), and reports the gap.

It deliberately does NOT compare against the stored nb_jours. In the demo data
that value is a random calendar span from demo/simulate_day.py, so comparing to
it would mostly measure weekends and wildly overstate the problem. On real client
data the stored value equals the old rule and the two approaches agree.

    python scripts/audit_holiday_conges.py           # report only
    python scripts/audit_holiday_conges.py --fix     # subtract the holiday days

Only annual leave affects the balance, but every type is reported.
--fix changes stored values; back up the database first.
"""
import argparse
import os
import sys
from collections import defaultdict
from datetime import timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import SessionLocal
from models.models import Conge, Employe, JourFerie
from services.holiday_service import working_days_between


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit leave requests spanning public holidays")
    ap.add_argument("--fix", action="store_true", help="correct the stored nb_jours")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        if db.query(JourFerie).count() == 0:
            print("No holidays stored. Run scripts/seed_holidays.py first.")
            return

        conges = db.query(Conge).all()
        if not conges:
            print("No leave records found.")
            return

        feries = {j.date_ferie for j in db.query(JourFerie).filter(JourFerie.chome == True).all()}  # noqa: E712

        def old_rule(start, end):
            """Weekends only - how the app counted before the holiday calendar."""
            n, cur = 0, start
            while cur <= end:
                if cur.weekday() < 5:
                    n += 1
                cur += timedelta(days=1)
            return n

        wrong = []
        for c in conges:
            if not c.date_debut or not c.date_fin or c.date_fin < c.date_debut:
                continue
            was = old_rule(c.date_debut, c.date_fin)
            now = working_days_between(db, c.date_debut, c.date_fin)
            if was != now:
                wrong.append((c, was, now, was - now))

        if not wrong:
            print(f"Clean - none of your {len(conges)} leave records span a public holiday.")
            return

        # Only annual leave is deducted from the balance.
        overcharged = defaultdict(int)
        for c, _was, _now, diff in wrong:
            if (c.type_conge or "Annuel") == "Annuel":
                overcharged[c.employe_id] += diff

        print(f"{len(wrong)} of {len(conges)} leave records span a public holiday.\n")
        print("  id     employee                  period                       old -> new")
        for c, was, now, diff in sorted(wrong, key=lambda r: -r[3])[:30]:
            emp = db.query(Employe).filter(Employe.employe_id == c.employe_id).first()
            name = f"{emp.nom} {emp.prenom}"[:24] if emp else f"#{c.employe_id}"
            print(f"  {c.conge_id:<6} {name:<25} {c.date_debut} to {c.date_fin}   "
                  f"{was} -> {now}  (-{diff})")
        if len(wrong) > 30:
            print(f"  ... and {len(wrong) - 30} more")

        if overcharged:
            total = sum(overcharged.values())
            avg = total / len(overcharged)
            print(f"\n{total} annual-leave days over-charged across "
                  f"{len(overcharged)} employees ({avg:.1f} days each on average).")
            print("Those days are owed back to their balance.")

        # Requests that consist entirely of holidays. Correcting these to zero is
        # not possible (and not meaningful) - they should be cancelled outright.
        empty = [(c, was) for c, was, _now, diff in wrong
                 if c.nb_jours is not None and c.nb_jours - diff < 1]
        if empty:
            print(f"\n{len(empty)} requests cover ONLY public holidays - "
                  f"they should be cancelled and refunded in full:")
            for c, was in empty[:15]:
                emp = db.query(Employe).filter(Employe.employe_id == c.employe_id).first()
                name = f"{emp.nom} {emp.prenom}"[:24] if emp else f"#{c.employe_id}"
                print(f"  {c.conge_id:<6} {name:<25} {c.date_debut} to {c.date_fin}"
                      f"   ({c.type_conge}, {c.statut})")
            if len(empty) > 15:
                print(f"  ... and {len(empty) - 15} more")
            print("  --fix leaves these alone; cancelling a request is HR's call.")

        if not args.fix:
            print("\nRun again with --fix to correct the stored values.")
            return

        if not args.yes:
            print(f"\nAbout to UPDATE {len(wrong)} leave records. Back up your database first.")
            if input("Type 'fix' to confirm: ").strip().lower() != "fix":
                print("Cancelled - nothing was changed.")
                return

        # Subtract only the holiday days. This keeps whatever baseline the record
        # already had rather than recomputing from scratch, so the correction is
        # exactly the bug being fixed and nothing else.
        #
        # A result of zero means the request covered nothing but holidays. The
        # schema forbids nb_jours <= 0 (CK_Conge_nb_jours), and rightly so - a
        # zero-day leave request is meaningless. Those are left untouched and
        # listed instead, because the correct action is to cancel the request and
        # refund it in full, which is HR's decision, not this script's.
        updated = 0
        for c, _was, _now, diff in wrong:
            if c.nb_jours is None:
                continue
            if c.nb_jours - diff >= 1:
                c.nb_jours = c.nb_jours - diff
                updated += 1
        db.commit()
        print(f"\nCorrected {updated} leave records.")
        if empty:
            print(f"{len(empty)} left unchanged - they cover only holidays and "
                  f"need to be cancelled by hand.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
