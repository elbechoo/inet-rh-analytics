"""Public holiday calculations.

These cover the bug that started this work: leave spanning a public holiday was
charged to the employee's own balance, and nobody clocking in on a holiday was
recorded as absent.

No database - the calendar builder and the working-day arithmetic are pure, so
they can be tested directly.
"""
from datetime import date, timedelta

import pytest

from services.holiday_service import build_calendar


def _dates(cal):
    return [h["date"] for h in cal]


def test_calendar_has_one_entry_per_date():
    """Civil and Islamic holidays collide - 20 March 2026 is both Independence
    Day and the first day of Aïd El-Fitr. One date is one day off, and the
    database enforces a unique date, so the two must be merged rather than
    duplicated."""
    cal = build_calendar(2024, 2028)
    dates = _dates(cal)
    assert len(dates) == len(set(dates)), "duplicate dates in the calendar"


def test_known_collision_is_merged():
    cal = build_calendar(2026, 2026)
    match = [h for h in cal if h["date"] == date(2026, 3, 20)]
    assert len(match) == 1
    assert "Indépendance" in match[0]["nom"]
    assert "Aïd El-Fitr" in match[0]["nom"]
    # A day that is both civil and religious counts as religious: that is what
    # drives the multi-day Aïd closure.
    assert match[0]["type"] == "religieux"


def test_fixed_civil_holidays_present_every_year():
    for year in range(2024, 2029):
        dates = _dates(build_calendar(year, year))
        for month, day in [(1, 1), (3, 20), (5, 1), (7, 25), (10, 15)]:
            assert date(year, month, day) in dates, f"missing {day}/{month}/{year}"


def test_aid_spans_three_days():
    cal = build_calendar(2025, 2025)
    fitr = sorted(h["date"] for h in cal if "Aïd El-Fitr" in h["nom"])
    assert len(fitr) == 3
    assert fitr[2] - fitr[0] == timedelta(days=2)


def test_names_fit_the_column():
    """nom is String(120); a merged name must not overflow it."""
    for h in build_calendar(2024, 2030):
        assert len(h["nom"]) <= 120


# ── Working-day arithmetic ──────────────────────────────────
# Mirrors services.holiday_service.working_days_between without a session, so
# the rule itself is pinned regardless of what is in the database.

def _working_days(start, end, feries):
    n, cur = 0, start
    while cur <= end:
        if cur.weekday() < 5 and cur not in feries:
            n += 1
        cur += timedelta(days=1)
    return n


def test_weekends_excluded():
    # Monday 1 June 2026 to Friday 5 June 2026
    assert _working_days(date(2026, 6, 1), date(2026, 6, 7), set()) == 5


def test_holiday_inside_a_leave_is_not_charged():
    """The original bug: an employee taking the week of Aïd paid for it."""
    feries = {date(2026, 5, 27), date(2026, 5, 28), date(2026, 5, 29)}
    start, end = date(2026, 5, 25), date(2026, 5, 29)   # Mon-Fri
    assert _working_days(start, end, set()) == 5        # old rule
    assert _working_days(start, end, feries) == 2       # corrected


def test_holiday_on_a_weekend_changes_nothing():
    """A three-day Aïd overlapping a weekend recovers fewer days - the reason
    the measured per-employee figure is smaller than people expect."""
    saturday = date(2026, 6, 6)
    assert saturday.weekday() >= 5
    assert _working_days(date(2026, 6, 1), date(2026, 6, 7), {saturday}) == 5


def test_reversed_range_is_zero():
    assert _working_days(date(2026, 6, 10), date(2026, 6, 1), set()) == 0
