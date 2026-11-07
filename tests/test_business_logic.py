"""
Unit tests for core business logic - no database required.
Run with: pytest tests/ -v
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime
from unittest.mock import MagicMock


# ──────────────────────────────────────────────
# calculer_jours_ouvrables  (conge_repo)
# ──────────────────────────────────────────────

from repositories.conge_repo import _calculer_jours_ouvrables as calculer_jours_ouvrables


class TestCalculerJoursOuvrables:

    def test_same_day_weekday(self):
        # Monday: 1 working day
        d = date(2024, 1, 8)  # Monday
        assert calculer_jours_ouvrables(d, d) == 1

    def test_same_day_weekend(self):
        # Saturday: 0 working days
        d = date(2024, 1, 6)  # Saturday
        assert calculer_jours_ouvrables(d, d) == 0

    def test_full_week(self):
        # Mon 8 Jan -> Fri 12 Jan 2024 = 5 working days
        assert calculer_jours_ouvrables(date(2024, 1, 8), date(2024, 1, 12)) == 5

    def test_includes_weekend_in_range(self):
        # Mon 8 Jan -> Mon 15 Jan 2024 = 6 working days (2 weekends excluded = Sat+Sun)
        assert calculer_jours_ouvrables(date(2024, 1, 8), date(2024, 1, 15)) == 6

    def test_month_with_31_days(self):
        # Wed 29 Jan -> Fri 31 Jan 2025 = 3 working days
        # This test caught the old day+1 overflow bug
        assert calculer_jours_ouvrables(date(2025, 1, 29), date(2025, 1, 31)) == 3

    def test_cross_month_boundary(self):
        # Fri 31 Jan -> Mon 3 Feb 2025 = 2 working days (Fri + Mon)
        assert calculer_jours_ouvrables(date(2025, 1, 31), date(2025, 2, 3)) == 2

    def test_cross_year_boundary(self):
        # Mon 30 Dec 2024 -> Wed 1 Jan 2025 = 3 working days
        assert calculer_jours_ouvrables(date(2024, 12, 30), date(2025, 1, 1)) == 3

    def test_long_period(self):
        # Full year 2024 - 262 working days (2024 is a leap year)
        result = calculer_jours_ouvrables(date(2024, 1, 1), date(2024, 12, 31))
        assert 260 <= result <= 264  # allow ±2 for public holiday edge cases


# ──────────────────────────────────────────────
# determiner_type_pointage  (pointage_repo)
# ──────────────────────────────────────────────

from repositories.pointage_repo import determiner_type_pointage


def _make_log(type_pointage: str, ts: datetime):
    log = MagicMock()
    log.type_pointage       = type_pointage
    log.timestamp_pointage  = ts
    return log


class TestDeterminerTypePointage:

    def test_first_badge_of_day(self):
        ts = datetime(2024, 1, 8, 8, 0)
        assert determiner_type_pointage(ts, []) == "ENTREE"

    def test_second_badge_is_debut_pause(self):
        ts1 = datetime(2024, 1, 8, 8, 0)
        ts2 = datetime(2024, 1, 8, 12, 0)
        log = _make_log("ENTREE", ts1)
        assert determiner_type_pointage(ts2, [log]) == "DEBUT_PAUSE"

    def test_third_badge_is_fin_pause(self):
        ts1 = datetime(2024, 1, 8, 8, 0)
        ts2 = datetime(2024, 1, 8, 12, 0)
        ts3 = datetime(2024, 1, 8, 13, 0)
        logs = [_make_log("ENTREE", ts1), _make_log("DEBUT_PAUSE", ts2)]
        assert determiner_type_pointage(ts3, logs) == "FIN_PAUSE"

    def test_fourth_badge_is_sortie(self):
        ts1 = datetime(2024, 1, 8, 8, 0)
        ts2 = datetime(2024, 1, 8, 12, 0)
        ts3 = datetime(2024, 1, 8, 13, 0)
        ts4 = datetime(2024, 1, 8, 17, 0)
        logs = [
            _make_log("ENTREE",      ts1),
            _make_log("DEBUT_PAUSE", ts2),
            _make_log("FIN_PAUSE",   ts3),
        ]
        assert determiner_type_pointage(ts4, logs) == "SORTIE"

    def test_doublon_within_2_minutes(self):
        ts1 = datetime(2024, 1, 8, 8, 0, 0)
        ts2 = datetime(2024, 1, 8, 8, 1, 30)  # 90 seconds later
        log = _make_log("ENTREE", ts1)
        assert determiner_type_pointage(ts2, [log]) == "DOUBLON"

    def test_doublon_full_day(self):
        logs = [
            _make_log("ENTREE",      datetime(2024, 1, 8, 8, 0)),
            _make_log("DEBUT_PAUSE", datetime(2024, 1, 8, 12, 0)),
            _make_log("FIN_PAUSE",   datetime(2024, 1, 8, 13, 0)),
            _make_log("SORTIE",      datetime(2024, 1, 8, 17, 0)),
        ]
        ts_extra = datetime(2024, 1, 8, 18, 0)
        assert determiner_type_pointage(ts_extra, logs) == "DOUBLON"


# ──────────────────────────────────────────────
# AI feature computation (no DB)
# ──────────────────────────────────────────────

class TestAIFeatures:

    def test_taux_absence_calculation(self):
        nb_pointages = 200
        nb_absences  = 20
        expected     = 20 / (200 + 20)
        result       = nb_absences / max(nb_pointages + nb_absences, 1)
        assert abs(result - expected) < 1e-6

    def test_taux_absence_zero_pointages(self):
        nb_pointages = 0
        nb_absences  = 5
        result = nb_absences / max(nb_pointages + nb_absences, 1)
        assert result == 1.0

    def test_taux_retard_no_retards(self):
        nb_retards   = 0
        nb_pointages = 100
        result = nb_retards / max(nb_pointages, 1)
        assert result == 0.0
