"""
iNET RH — Enhanced Demo Simulator
Employee profiles + seasonal patterns for realistic simulation.
  - 07:00 → Morning entries
  - 18:00 → Evening exits + leave requests
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
import logging
from datetime import datetime, date, timedelta, time
from sqlalchemy.orm import Session

from config.database import SessionLocal
from models.models import Employe, Pointage, PointageLog, Absence, Conge

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# EMPLOYEE PROFILES
# ─────────────────────────────────────────
# Deterministically assigned per employee — same employee always same profile.
# Distribution: 30% punctual, 40% normal, 20% often-late, 10% high-absentee

PROFILES = {
    "punctual": {
        "prob_absent":       0.02,
        "prob_late":         0.03,
        "entry_ontime_min": -15,  "entry_ontime_max":  5,   # 7:45 → 8:05
        "entry_late_min":    10,  "entry_late_max":   30,   # 8:10 → 8:30
        "exit_min":           0,  "exit_max":         20,   # 17:00 → 17:20
    },
    "normal": {
        "prob_absent":       0.07,
        "prob_late":         0.12,
        "entry_ontime_min":  -5,  "entry_ontime_max": 15,   # 7:55 → 8:15
        "entry_late_min":    20,  "entry_late_max":   60,   # 8:20 → 9:00
        "exit_min":           0,  "exit_max":         45,   # 17:00 → 17:45
    },
    "often_late": {
        "prob_absent":       0.05,
        "prob_late":         0.35,
        "entry_ontime_min":  15,  "entry_ontime_max": 30,   # 8:15 → 8:30
        "entry_late_min":    30,  "entry_late_max":   90,   # 8:30 → 9:30
        "exit_min":           0,  "exit_max":         60,   # 17:00 → 18:00
    },
    "high_absentee": {
        "prob_absent":       0.20,
        "prob_late":         0.08,
        "entry_ontime_min":   0,  "entry_ontime_max": 30,   # 8:00 → 8:30
        "entry_late_min":     5,  "entry_late_max":   40,   # 8:05 → 8:40
        "exit_min":         -30,  "exit_max":         30,   # 16:30 → 17:30
    },
}

PROFILE_THRESHOLDS = [
    ("punctual",      0.30),
    ("normal",        0.70),
    ("often_late",    0.90),
    ("high_absentee", 1.00),
]


def get_profile(employe_id: int) -> dict:
    """Deterministically assign a behavior profile based on employe_id."""
    rng = random.Random(employe_id * 7919)
    r = rng.random()
    for name, threshold in PROFILE_THRESHOLDS:
        if r < threshold:
            return PROFILES[name]
    return PROFILES["normal"]


# ─────────────────────────────────────────────────────────────
# BEHAVIOURAL DRIFT
# ─────────────────────────────────────────────────────────────
# A fixed profile per employee means nobody's behaviour ever changes, so the
# question HR actually cares about — "who is getting worse?" — has no answer in
# the data, and no model can learn it. Real workforces do not behave that way:
# disengagement builds over months and shows up in attendance well before a
# resignation.
#
# A minority of employees therefore enter a decline phase at some point in their
# history, during which their absence probability ramps up. A few recover. The
# pattern is deterministic per employee so re-running the seeder reproduces it.
DRIFT_SHARE      = 0.22   # share of employees who drift at some point
RECOVERY_SHARE   = 0.35   # of those, the share who recover afterwards
DRIFT_RAMP_DAYS  = 150    # how long the decline takes to reach full strength
DRIFT_PEAK_MULT  = 3.2    # absence probability multiplier at the worst point


def _drift_plan(employe_id: int) -> dict | None:
    """When (if ever) this employee's attendance starts to deteriorate."""
    rng = random.Random(employe_id * 104729 + 17)
    if rng.random() >= DRIFT_SHARE:
        return None
    return {
        # Offset in days from the start of the simulated period.
        "start_offset": rng.randint(120, 900),
        "recovers": rng.random() < RECOVERY_SHARE,
        "recovery_after": rng.randint(120, 260),
        "peak": DRIFT_PEAK_MULT * rng.uniform(0.7, 1.3),
    }


# Anchor for drift timing. Set once per process by the seeder so every day of a
# backfill shares the same reference; defaults to a fixed date otherwise.
_DRIFT_EPOCH: date | None = None


def set_drift_epoch(d: date) -> None:
    global _DRIFT_EPOCH
    _DRIFT_EPOCH = d


def drift_multiplier(employe_id: int, target_date: date) -> float:
    """How much this employee's absence tendency is elevated on this date.

    1.0 means unchanged. Rises gradually through the decline phase rather than
    stepping, so the trend is visible in a rolling window — which is exactly the
    signal the deterioration model is meant to pick up.
    """
    plan = _drift_plan(employe_id)
    if plan is None:
        return 1.0

    epoch = _DRIFT_EPOCH or date(target_date.year - 3, 1, 1)
    day = (target_date - epoch).days
    start = plan["start_offset"]
    if day < start:
        return 1.0

    since = day - start
    if plan["recovers"] and since > plan["recovery_after"]:
        # Improvement is faster than decline — a resolved problem, not a slow fade.
        fade = (since - plan["recovery_after"]) / 90.0
        if fade >= 1.0:
            return 1.0
        peak_at_recovery = 1.0 + (plan["peak"] - 1.0) * min(
            plan["recovery_after"] / DRIFT_RAMP_DAYS, 1.0
        )
        return 1.0 + (peak_at_recovery - 1.0) * (1.0 - fade)

    ramp = min(since / DRIFT_RAMP_DAYS, 1.0)
    return 1.0 + (plan["peak"] - 1.0) * ramp


# ─────────────────────────────────────────
# SEASONAL HELPERS
# ─────────────────────────────────────────
RAMADAN_PERIODS = [
    (date(2024, 3, 11), date(2024, 4,  9)),
    (date(2025, 3,  1), date(2025, 3, 29)),
    (date(2026, 2, 17), date(2026, 3, 17)),
]


def is_ramadan(d: date) -> bool:
    return any(start <= d <= end for start, end in RAMADAN_PERIODS)


def is_summer(d: date) -> bool:
    return d.month in (6, 7, 8)


def is_winter(d: date) -> bool:
    return d.month in (12, 1)


def absence_multiplier(d: date) -> float:
    """Winter illness spikes."""
    return 1.4 if is_winter(d) else 1.0


def conge_probability(d: date) -> float:
    """Summer: many more leave requests."""
    return 0.18 if is_summer(d) else 0.04


# ─────────────────────────────────────────
# ABSENCE MOTIFS
# ─────────────────────────────────────────
MOTIFS_UNJUSTIFIED = [
    "Unjustified absence",
    "Personal reason",
    "Transport issue",
    "No notice given",
]
MOTIFS_WINTER_SICK = [
    "Sick leave (unverified)",
    "Illness",
    "Medical appointment",
]
MOTIFS_JUSTIFIED = [
    "Medical certificate",
    "Family emergency",
    "Administrative appointment",
    "Maternity/paternity leave",
]

TYPES_CONGE        = ["Annuel", "Maladie", "Familial", "Sans solde"]
TYPES_CONGE_SUMMER = ["Annuel", "Annuel", "Annuel", "Familial"]  # summer weighted toward Annuel


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
HEURE_ENTREE_NORMALE = time(8, 0)


def rand_time(base: time, delta_min: int, delta_max: int, for_date: date) -> time:
    base_dt = datetime.combine(for_date, base)
    minutes = random.randint(delta_min, delta_max)
    return (base_dt + timedelta(minutes=minutes)).time()


def already_pointed(db: Session, employe_id: int, type_p: str, d: date) -> bool:
    return db.query(PointageLog).filter(
        PointageLog.employe_id         == employe_id,
        PointageLog.timestamp_pointage >= datetime.combine(d, time(0, 0)),
        PointageLog.timestamp_pointage <  datetime.combine(d + timedelta(days=1), time(0, 0)),
        PointageLog.type_pointage      == type_p,
    ).first() is not None


def has_absence_record(db: Session, employe_id: int, d: date) -> bool:
    return db.query(Absence).filter(
        Absence.employe_id   == employe_id,
        Absence.date_absence == d,
    ).first() is not None


def get_or_create_pointage(db: Session, employe_id: int, d: date) -> Pointage:
    p = db.query(Pointage).filter(
        Pointage.employe_id    == employe_id,
        Pointage.date_pointage == d,
    ).first()
    if not p:
        p = Pointage(employe_id=employe_id, date_pointage=d, statut="Présent")
        db.add(p)
        db.flush()
    return p


# ─────────────────────────────────────────
# PUBLIC HOLIDAYS
# ─────────────────────────────────────────
_FERIES_CACHE: set | None = None


def _is_ferie(db: Session, d: date) -> bool:
    """Is this a non-working public holiday?

    The whole calendar is loaded once per process — the seeder calls this for
    every day of every year, and one query per day would dominate its runtime.
    Returns False if the calendar has not been seeded, so simulation still
    works on a database without holidays.
    """
    global _FERIES_CACHE
    if _FERIES_CACHE is None:
        try:
            from models.models import JourFerie
            rows = db.query(JourFerie.date_ferie).filter(JourFerie.chome == True).all()  # noqa: E712
            _FERIES_CACHE = {r[0] for r in rows}
        except Exception:
            _FERIES_CACHE = set()
    return d in _FERIES_CACHE


# ─────────────────────────────────────────
# CORE SIMULATION — ENTRIES
# ─────────────────────────────────────────
def simulate_day_entrees(db: Session, target_date: date) -> dict:
    """Simulate morning entries for all active employees on target_date."""
    if target_date.weekday() >= 5:
        return {"skipped": "weekend"}
    if _is_ferie(db, target_date):
        # Nobody clocks in on a public holiday. Generating absences for these
        # days would fabricate a company-wide absence spike and feed the
        # absenteeism model days when nobody was expected at work.
        return {"skipped": "holiday"}

    employes = db.query(Employe).filter(Employe.statut == "Actif").all()
    nb_presents = nb_retards = nb_absents = 0
    ramadan = is_ramadan(target_date)
    abs_mult = absence_multiplier(target_date)

    for emp in employes:
        if already_pointed(db, emp.employe_id, "ENTREE", target_date):
            continue
        if has_absence_record(db, emp.employe_id, target_date):
            continue

        profile     = get_profile(emp.employe_id)
        drift       = drift_multiplier(emp.employe_id, target_date)
        prob_absent = min(profile["prob_absent"] * abs_mult * drift, 0.40)
        # Lateness drifts too, but less sharply — disengagement shows up as
        # absence first and punctuality second.
        prob_late   = min(profile["prob_late"] * (1.0 + (drift - 1.0) * 0.45), 0.60)
        r           = random.random()

        if r < prob_absent:
            # ABSENT — only create Absence record, no Pointage row
            justifiee = random.random() < 0.30
            if justifiee:
                motifs = MOTIFS_JUSTIFIED
            elif is_winter(target_date):
                motifs = MOTIFS_WINTER_SICK
            else:
                motifs = MOTIFS_UNJUSTIFIED

            db.add(Absence(
                employe_id   = emp.employe_id,
                date_absence = target_date,
                justifiee    = justifiee,
                motif        = random.choice(motifs),
                statut       = "Justifiée" if justifiee else "Non justifiée",
            ))
            nb_absents += 1

        elif r < prob_absent + prob_late:
            # LATE
            if ramadan:
                heure_entree = rand_time(time(9, 0), 15, 60, target_date)
            else:
                heure_entree = rand_time(
                    HEURE_ENTREE_NORMALE,
                    profile["entry_late_min"],
                    profile["entry_late_max"],
                    target_date,
                )
            retard = max(0, int((
                datetime.combine(target_date, heure_entree) -
                datetime.combine(target_date, HEURE_ENTREE_NORMALE)
            ).total_seconds() / 60))

            db.add(PointageLog(
                employe_id         = emp.employe_id,
                timestamp_pointage = datetime.combine(target_date, heure_entree),
                type_pointage      = "ENTREE",
                source             = "simulation",
            ))
            p = get_or_create_pointage(db, emp.employe_id, target_date)
            p.heure_entree   = heure_entree
            p.retard_minutes = retard
            p.statut         = "En retard"
            nb_retards += 1

        else:
            # ON TIME
            if ramadan:
                heure_entree = rand_time(time(9, 0), 0, 20, target_date)
                retard = 0
            else:
                heure_entree = rand_time(
                    HEURE_ENTREE_NORMALE,
                    profile["entry_ontime_min"],
                    profile["entry_ontime_max"],
                    target_date,
                )
                retard = 0

            db.add(PointageLog(
                employe_id         = emp.employe_id,
                timestamp_pointage = datetime.combine(target_date, heure_entree),
                type_pointage      = "ENTREE",
                source             = "simulation",
            ))
            p = get_or_create_pointage(db, emp.employe_id, target_date)
            p.heure_entree   = heure_entree
            p.retard_minutes = retard
            p.statut         = "Présent"
            nb_presents += 1

    db.commit()
    return {"presents": nb_presents, "retards": nb_retards, "absents": nb_absents}


# ─────────────────────────────────────────
# CORE SIMULATION — EXITS
# ─────────────────────────────────────────
def simulate_day_sorties(db: Session, target_date: date) -> dict:
    """Simulate evening exits and leave requests for target_date."""
    if target_date.weekday() >= 5:
        return {"skipped": "weekend"}
    if _is_ferie(db, target_date):
        return {"skipped": "holiday"}

    employes = db.query(Employe).filter(Employe.statut == "Actif").all()
    nb_sorties = nb_manquantes = nb_bonne_heure = nb_conges = 0
    ramadan    = is_ramadan(target_date)
    prob_conge = conge_probability(target_date)

    for emp in employes:
        p = db.query(Pointage).filter(
            Pointage.employe_id    == emp.employe_id,
            Pointage.date_pointage == target_date,
        ).first()

        if not p or p.heure_entree is None:
            continue
        if already_pointed(db, emp.employe_id, "SORTIE", target_date):
            continue

        profile = get_profile(emp.employe_id)
        r = random.random()

        if ramadan:
            exit_base, exit_min, exit_max = time(15, 30), 0, 60
            early_base = time(15, 0)
        else:
            exit_base = time(17, 0)
            exit_min  = profile["exit_min"]
            exit_max  = profile["exit_max"]
            early_base = time(16, 0)

        if r < 0.05:
            # MISSING EXIT (5%)
            p.statut       = "Sortie manquante"
            p.heure_sortie = None
            nb_manquantes += 1

        elif r < 0.10:
            # EARLY EXIT (5%)
            heure_sortie = rand_time(early_base, 0, 59, target_date)
            db.add(PointageLog(
                employe_id         = emp.employe_id,
                timestamp_pointage = datetime.combine(target_date, heure_sortie),
                type_pointage      = "SORTIE",
                source             = "simulation",
            ))
            p.heure_sortie  = heure_sortie
            p.duree_travail = round((
                datetime.combine(target_date, heure_sortie) -
                datetime.combine(target_date, p.heure_entree)
            ).total_seconds() / 3600, 2)
            nb_bonne_heure += 1

        else:
            # NORMAL EXIT (90%)
            heure_sortie = rand_time(exit_base, exit_min, exit_max, target_date)
            db.add(PointageLog(
                employe_id         = emp.employe_id,
                timestamp_pointage = datetime.combine(target_date, heure_sortie),
                type_pointage      = "SORTIE",
                source             = "simulation",
            ))
            p.heure_sortie  = heure_sortie
            p.duree_travail = round((
                datetime.combine(target_date, heure_sortie) -
                datetime.combine(target_date, p.heure_entree)
            ).total_seconds() / 3600, 2)
            nb_sorties += 1

        # LEAVE REQUEST (seasonal probability)
        if random.random() < prob_conge:
            date_debut = target_date + timedelta(days=random.randint(3, 30))
            nb_jours   = random.randint(2, 14) if is_summer(target_date) else random.randint(1, 7)
            date_fin   = date_debut + timedelta(days=nb_jours - 1)
            types      = TYPES_CONGE_SUMMER if is_summer(target_date) else TYPES_CONGE
            db.add(Conge(
                employe_id  = emp.employe_id,
                type_conge  = random.choice(types),
                date_debut  = date_debut,
                date_fin    = date_fin,
                nb_jours    = nb_jours,
                statut      = "En attente",
                commentaire = "Auto-generated by simulation",
            ))
            nb_conges += 1

    db.commit()
    return {
        "sorties":      nb_sorties,
        "manquantes":   nb_manquantes,
        "bonne_heure":  nb_bonne_heure,
        "conges":       nb_conges,
    }


# ─────────────────────────────────────────
# PUBLIC API (called by scheduler)
# ─────────────────────────────────────────
def simulate_entrees():
    logger.info("=" * 50)
    logger.info(f"SIMULATION ENTRIES — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    logger.info("=" * 50)
    db = SessionLocal()
    try:
        result = simulate_day_entrees(db, date.today())
        if "skipped" in result:
            logger.info("Weekend — simulation skipped")
        else:
            logger.info(
                f"Entries done: {result['presents']} present, "
                f"{result['retards']} late, {result['absents']} absent"
            )
    finally:
        db.close()


def simulate_sorties_et_conges():
    logger.info("=" * 50)
    logger.info(f"SIMULATION EXITS + LEAVE — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    logger.info("=" * 50)
    db = SessionLocal()
    try:
        result = simulate_day_sorties(db, date.today())
        if "skipped" in result:
            logger.info("Weekend — simulation skipped")
        else:
            logger.info(
                f"Exits done: {result['sorties']} normal, "
                f"{result['bonne_heure']} early, "
                f"{result['manquantes']} missing | "
                f"{result['conges']} leave requests"
            )
    finally:
        db.close()


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="iNET RH — Enhanced Simulator")
    parser.add_argument("--entrees", action="store_true", help="Simulate entries only")
    parser.add_argument("--sorties", action="store_true", help="Simulate exits + leave only")
    parser.add_argument("--all",     action="store_true", help="Simulate entries + exits")
    parser.add_argument("--date",    type=str, default=None, help="Target date YYYY-MM-DD (default: today)")
    args = parser.parse_args()

    target = date.today()
    if args.date:
        from datetime import date as dt_date
        target = dt_date.fromisoformat(args.date)

    def _run_entrees():
        logger.info("=" * 50)
        logger.info(f"SIMULATION ENTRIES — {target.strftime('%d/%m/%Y')}")
        logger.info("=" * 50)
        db = SessionLocal()
        try:
            result = simulate_day_entrees(db, target)
            if "skipped" in result:
                logger.info("Weekend — simulation skipped")
            else:
                logger.info(
                    f"Entries done: {result['presents']} present, "
                    f"{result['retards']} late, {result['absents']} absent"
                )
        finally:
            db.close()

    def _run_sorties():
        logger.info("=" * 50)
        logger.info(f"SIMULATION EXITS + LEAVE — {target.strftime('%d/%m/%Y')}")
        logger.info("=" * 50)
        db = SessionLocal()
        try:
            result = simulate_day_sorties(db, target)
            if "skipped" in result:
                logger.info("Weekend — simulation skipped")
            else:
                logger.info(
                    f"Exits done: {result['sorties']} normal, "
                    f"{result['bonne_heure']} early, "
                    f"{result['manquantes']} missing | "
                    f"{result['conges']} leave requests"
                )
        finally:
            db.close()

    if args.entrees:
        _run_entrees()
    elif args.sorties:
        _run_sorties()
    elif args.all:
        _run_entrees()
        _run_sorties()
    else:
        parser.print_help()
