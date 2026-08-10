"""Public holidays — the single source of truth for "is this a working day".

Everything that counts days (leave deduction, absence detection, attendance
rates, the absenteeism model) must go through here, otherwise a public holiday
looks like an absence.

Islamic holidays move about 11 days earlier each Gregorian year and the exact
date is fixed by moon sighting, announced days in advance. They are therefore
stored per year rather than computed, and HR can correct a date when the
official announcement differs from the estimate.
"""
from datetime import date, timedelta
from functools import lru_cache

from sqlalchemy.orm import Session

from models.models import JourFerie

# ── Fixed civil holidays (Tunisia) ──────────────────────────
# (month, day, name)
FIXED = [
    (1,  1,  "Nouvel An"),
    (1,  14, "Fête de la Révolution et de la Jeunesse"),
    (3,  20, "Fête de l'Indépendance"),
    (4,  9,  "Journée des Martyrs"),
    (5,  1,  "Fête du Travail"),
    (7,  25, "Fête de la République"),
    (8,  13, "Fête de la Femme"),
    (10, 15, "Fête de l'Évacuation"),
]

# ── Islamic holidays, official Tunisian dates ───────────────
# Estimates beyond the announced year — HR should confirm each year.
# name: [(year, month, day, duration_days)]
ISLAMIC = {
    "Aïd El-Fitr": [
        (2024, 4, 10, 3), (2025, 3, 30, 3), (2026, 3, 20, 3),
        (2027, 3, 9, 3),  (2028, 2, 26, 3),
    ],
    "Aïd El-Idha": [
        (2024, 6, 16, 3), (2025, 6, 6, 3),  (2026, 5, 27, 3),
        (2027, 5, 16, 3), (2028, 5, 5, 3),
    ],
    "Ras El Am Hejri": [
        (2024, 7, 7, 1),  (2025, 6, 26, 1), (2026, 6, 16, 1),
        (2027, 6, 6, 1),  (2028, 5, 25, 1),
    ],
    "Mouled": [
        (2024, 9, 15, 1), (2025, 9, 4, 1),  (2026, 8, 25, 1),
        (2027, 8, 14, 1), (2028, 8, 3, 1),
    ],
}


def build_calendar(year_from: int, year_to: int) -> list[dict]:
    """Return every holiday between the two years, inclusive — one entry per date.

    Civil and Islamic holidays do collide: in 2026 Aïd El-Fitr falls on 20 March,
    which is also Independence Day. One date is still one non-working day, so the
    two are merged into a single entry rather than duplicated — the day off does
    not double up, and the date stays unique in the database.
    """
    by_date: dict[date, dict] = {}

    def add(d: date, nom: str, type_: str) -> None:
        existing = by_date.get(d)
        if existing is None:
            by_date[d] = {"date": d, "nom": nom, "type": type_}
            return
        if nom not in existing["nom"]:
            existing["nom"] = f"{existing['nom']} / {nom}"[:120]
        # A day that is both civil and religious is recorded as religious,
        # since that is what drives the multi-day Aïd closure.
        if type_ == "religieux":
            existing["type"] = "religieux"

    for y in range(year_from, year_to + 1):
        for m, d, name in FIXED:
            add(date(y, m, d), name, "civil")

    for name, entries in ISLAMIC.items():
        for (y, m, d, span) in entries:
            if year_from <= y <= year_to:
                start = date(y, m, d)
                for i in range(span):
                    label = name if span == 1 else f"{name} (J{i + 1})"
                    add(start + timedelta(days=i), label, "religieux")

    return [by_date[k] for k in sorted(by_date)]


def seed(db: Session, year_from: int, year_to: int, overwrite: bool = False) -> dict:
    """Write the calendar into the database. Existing dates are left alone
    unless `overwrite` is set, so HR corrections survive a re-seed."""
    created = updated = skipped = 0
    for h in build_calendar(year_from, year_to):
        existing = db.query(JourFerie).filter(JourFerie.date_ferie == h["date"]).first()
        if existing:
            if overwrite:
                existing.nom = h["nom"]
                existing.type_ferie = h["type"]
                updated += 1
            else:
                skipped += 1
            continue
        db.add(JourFerie(date_ferie=h["date"], nom=h["nom"],
                         type_ferie=h["type"], chome=True))
        created += 1
    db.commit()
    return {"created": created, "updated": updated, "skipped": skipped}


def holiday_dates(db: Session, start: date, end: date) -> set[date]:
    """Non-working holiday dates in a range."""
    rows = db.query(JourFerie.date_ferie).filter(
        JourFerie.date_ferie >= start,
        JourFerie.date_ferie <= end,
        JourFerie.chome == True,        # noqa: E712 — SQLAlchemy needs ==
    ).all()
    return {r[0] for r in rows}


def is_holiday(db: Session, d: date) -> bool:
    return db.query(JourFerie).filter(
        JourFerie.date_ferie == d, JourFerie.chome == True,  # noqa: E712
    ).first() is not None


def is_working_day(db: Session, d: date) -> bool:
    """Monday-Friday and not a public holiday."""
    if d.weekday() >= 5:
        return False
    return not is_holiday(db, d)


def working_days_between(db: Session, start: date, end: date) -> int:
    """Working days in an inclusive range, excluding weekends and holidays.

    This is what leave deduction must use — otherwise an employee taking a week
    that contains Aïd pays for the holiday out of their own balance.
    """
    if end < start:
        return 0
    feries = holiday_dates(db, start, end)
    n = 0
    cur = start
    while cur <= end:
        if cur.weekday() < 5 and cur not in feries:
            n += 1
        cur += timedelta(days=1)
    return n
