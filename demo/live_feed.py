"""iNET RH — live demo feed.

`simulate_day.py` writes a whole day in one shot, which is right for seeding
history but wrong for a demo: by the time you open the dashboard, everything has
already happened and nothing moves.

This drips the same events in one at a time so the dashboard changes while
somebody is watching it. Numbers climb, rows appear, charts shift.

Usage
-----
    python demo/live_feed.py                 # one arrival every ~6s
    python demo/live_feed.py --interval 3    # faster, for a short demo
    python demo/live_feed.py --burst 5       # 5 people at a time
    python demo/live_feed.py --reset         # clear today first, then feed
    python demo/live_feed.py --exits         # feed evening exits instead

Stop with Ctrl+C at any time — everything written so far stays.
"""
import argparse
import os
import random
import sys
import time as _time
from datetime import date, datetime, time, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from config.database import SessionLocal
from models.models import Employe, Pointage, PointageLog, Absence

from demo.simulate_day import (
    get_profile, rand_time, already_pointed, has_absence_record,
    get_or_create_pointage, absence_multiplier, is_ramadan, is_winter,
    HEURE_ENTREE_NORMALE, MOTIFS_JUSTIFIED, MOTIFS_UNJUSTIFIED, MOTIFS_WINTER_SICK,
)

GREEN = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"; DIM = "\033[2m"; OFF = "\033[0m"


def reset_today(db: Session, today: date) -> None:
    """Wipe today's punches and absences so the feed can replay the day."""
    n_logs = db.query(PointageLog).filter(
        PointageLog.timestamp_pointage >= datetime.combine(today, time.min),
        PointageLog.timestamp_pointage <= datetime.combine(today, time.max),
    ).delete(synchronize_session=False)
    n_ptg = db.query(Pointage).filter(Pointage.date_pointage == today).delete(synchronize_session=False)
    n_abs = db.query(Absence).filter(Absence.date_absence == today).delete(synchronize_session=False)
    db.commit()
    print(f"{DIM}reset — removed {n_ptg} punches, {n_logs} logs, {n_abs} absences for {today}{OFF}")


def feed_one_arrival(db: Session, emp: Employe, today: date) -> str | None:
    """Write a single arrival (or absence) for one employee. Returns a label."""
    if already_pointed(db, emp.employe_id, "ENTREE", today):
        return None
    if has_absence_record(db, emp.employe_id, today):
        return None

    profile = get_profile(emp.employe_id)
    prob_absent = min(profile["prob_absent"] * absence_multiplier(today), 0.40)
    prob_late = profile["prob_late"]
    r = random.random()
    name = f"{emp.prenom} {emp.nom}"

    if r < prob_absent:
        justifiee = random.random() < 0.30
        motifs = (MOTIFS_JUSTIFIED if justifiee
                  else MOTIFS_WINTER_SICK if is_winter(today)
                  else MOTIFS_UNJUSTIFIED)
        db.add(Absence(
            employe_id=emp.employe_id, date_absence=today,
            justifiee=justifiee, motif=random.choice(motifs),
            statut="Justifiée" if justifiee else "Non justifiée",
        ))
        db.commit()
        return f"{RED}absent {OFF}{name}{DIM} — {'justified' if justifiee else 'unjustified'}{OFF}"

    late = r < prob_absent + prob_late
    if late:
        heure = (rand_time(time(9, 0), 15, 60, today) if is_ramadan(today)
                 else rand_time(HEURE_ENTREE_NORMALE,
                                profile["entry_late_min"], profile["entry_late_max"], today))
    else:
        heure = rand_time(HEURE_ENTREE_NORMALE,
                          profile["entry_ontime_min"], profile["entry_ontime_max"], today)

    retard = max(0, int((
        datetime.combine(today, heure) - datetime.combine(today, HEURE_ENTREE_NORMALE)
    ).total_seconds() / 60))

    db.add(PointageLog(
        employe_id=emp.employe_id,
        timestamp_pointage=datetime.combine(today, heure),
        type_pointage="ENTREE",
    ))
    p = get_or_create_pointage(db, emp.employe_id, today)
    p.heure_entree = heure
    p.retard_minutes = retard
    p.statut = "En retard" if retard > 0 else "Présent"
    db.commit()

    if retard > 0:
        return f"{YELLOW}late   {OFF}{name}{DIM} — {heure.strftime('%H:%M')} (+{retard} min){OFF}"
    return f"{GREEN}on time{OFF} {name}{DIM} — {heure.strftime('%H:%M')}{OFF}"


def feed_one_exit(db: Session, p: Pointage, today: date) -> str | None:
    """Close out one open punch with an exit time."""
    if p.heure_sortie or not p.heure_entree:
        return None
    emp = db.query(Employe).filter(Employe.employe_id == p.employe_id).first()
    if not emp:
        return None
    profile = get_profile(p.employe_id)
    sortie = rand_time(time(17, 0), profile["exit_min"], profile["exit_max"], today)
    p.heure_sortie = sortie
    worked = (datetime.combine(today, sortie) - datetime.combine(today, p.heure_entree))
    p.duree_travail = round(worked.total_seconds() / 3600, 2)
    db.add(PointageLog(
        employe_id=p.employe_id,
        timestamp_pointage=datetime.combine(today, sortie),
        type_pointage="SORTIE",
    ))
    db.commit()
    return f"{DIM}exit   {emp.prenom} {emp.nom} — {sortie.strftime('%H:%M')} ({p.duree_travail}h){OFF}"


def main() -> None:
    ap = argparse.ArgumentParser(description="iNET RH — live demo feed")
    ap.add_argument("--interval", type=float, default=6.0, help="seconds between events (default 6)")
    ap.add_argument("--burst", type=int, default=1, help="events per tick (default 1)")
    ap.add_argument("--reset", action="store_true", help="clear today before feeding")
    ap.add_argument("--exits", action="store_true", help="feed exits instead of arrivals")
    ap.add_argument("--date", type=str, default=None, help="target date YYYY-MM-DD (default today)")
    args = ap.parse_args()

    today = date.fromisoformat(args.date) if args.date else date.today()
    db = SessionLocal()

    try:
        if args.reset:
            reset_today(db, today)

        if args.exits:
            queue = db.query(Pointage).filter(
                Pointage.date_pointage == today,
                Pointage.heure_sortie.is_(None),
                Pointage.heure_entree.isnot(None),
            ).all()
            label = "exits"
        else:
            done = {r[0] for r in db.query(Pointage.employe_id).filter(
                Pointage.date_pointage == today, Pointage.heure_entree.isnot(None)).all()}
            absent = {r[0] for r in db.query(Absence.employe_id).filter(
                Absence.date_absence == today).all()}
            queue = [e for e in db.query(Employe).filter(Employe.statut == "Actif").all()
                     if e.employe_id not in done and e.employe_id not in absent]
            label = "arrivals"

        random.shuffle(queue)
        total = len(queue)
        if not total:
            print(f"nothing left to feed for {today} ({label} already complete). "
                  f"Use --reset to replay the day.")
            return

        print(f"feeding {total} {label} for {today} — one every {args.interval}s "
              f"(burst {args.burst}). Ctrl+C to stop.\n")

        sent = 0
        for i in range(0, total, args.burst):
            for item in queue[i:i + args.burst]:
                line = (feed_one_exit(db, item, today) if args.exits
                        else feed_one_arrival(db, item, today))
                if line:
                    sent += 1
                    print(f"  [{sent:>3}/{total}] {line}")
            if i + args.burst < total:
                _time.sleep(args.interval)

        print(f"\ndone — {sent} events written for {today}.")
    except KeyboardInterrupt:
        print(f"\n{DIM}stopped — everything written so far is saved.{OFF}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
