"""Explainable AI — turn a risk score into human-readable reasons.

The Random Forest already exposes `feature_importances_`, but a bare
"73% risk" tells an HR manager nothing actionable. This module converts each
prediction into plain sentences such as:

    "Absence rate is 3.1x the company average (12.4% vs 4.0%)"
    "18 late arrivals - well above the typical 5"

Method
------
For every feature we compare the employee's value against the cohort (all
active employees) and score how unusual it is:

    deviation = (value - cohort_median) / cohort_spread

That deviation is weighted by the model's own feature importance, so the
reasons we surface are the ones the model actually relied on - not just any
number that happens to look large. The top contributors are returned, each with
the raw value, the cohort baseline, and a severity band.

This is a *local, post-hoc* explanation (same family as SHAP, but dependency
free and fast enough to run inline with the prediction endpoint).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Per-feature presentation metadata.
#   worse: "high" -> larger values indicate more risk; "low" -> smaller is worse
#   fmt:   how to render the value for a human
#   unit:  appended to the rendered number
FEATURE_META = {
    "taux_absence":       {"label": "Absence rate",        "worse": "high", "fmt": "pct",   "unit": "%"},
    "nb_absences":        {"label": "Total absences",      "worse": "high", "fmt": "int",   "unit": ""},
    "nb_absences_injust": {"label": "Unjustified absences","worse": "high", "fmt": "int",   "unit": ""},
    "taux_retard":        {"label": "Lateness rate",       "worse": "high", "fmt": "pct",   "unit": "%"},
    "nb_retards":         {"label": "Late arrivals",       "worse": "high", "fmt": "int",   "unit": ""},
    "moy_retard_min":     {"label": "Average lateness",    "worse": "high", "fmt": "float", "unit": " min"},
    "moy_heures_jour":    {"label": "Average hours/day",   "worse": "low",  "fmt": "float", "unit": " h"},
    "nb_conges":          {"label": "Leave days taken",    "worse": "high", "fmt": "int",   "unit": ""},
    "anciennete":         {"label": "Seniority",           "worse": "low",  "fmt": "int",   "unit": " mo"},
}

# Features that are contextual rather than behavioural. They can inform the
# model but make weak stand-alone "reasons", so they need a stronger signal.
_WEAK_AS_REASON = {"anciennete", "nb_conges"}


def _fmt(value: float, meta: dict) -> str:
    """Render a raw feature value the way a human would write it."""
    kind = meta["fmt"]
    if kind == "pct":
        # rates are stored 0-1 in the feature frame
        return f"{value * 100:.1f}{meta['unit']}"
    if kind == "int":
        return f"{int(round(value))}{meta['unit']}"
    return f"{value:.1f}{meta['unit']}"


def _severity(dev: float) -> str:
    """Bucket a deviation into a severity band used for UI colouring."""
    if dev >= 2.0:
        return "high"
    if dev >= 1.0:
        return "medium"
    return "low"


def build_cohort_stats(df: pd.DataFrame, features: list[str]) -> dict:
    """Pre-compute cohort baselines once per prediction run (not per employee).

    Spread uses the IQR, which is robust to the long tail of a few extreme
    absentees; it falls back to std, then to a small epsilon so we never divide
    by zero on uniform data.
    """
    stats = {}
    for f in features:
        if f not in df.columns:
            continue
        col = pd.to_numeric(df[f], errors="coerce").dropna()
        if col.empty:
            continue
        q1, q3 = col.quantile(0.25), col.quantile(0.75)
        iqr = float(q3 - q1)
        spread = iqr if iqr > 0 else float(col.std() or 0.0)
        if not spread or np.isnan(spread):
            spread = max(abs(float(col.median())) * 0.25, 1e-6)
        stats[f] = {
            "median": float(col.median()),
            "mean":   float(col.mean()),
            "spread": float(spread),
        }
    return stats


def explain_employee(
    row,
    cohort: dict,
    importances: dict | None = None,
    top_n: int = 3,
) -> list[dict]:
    """Return the strongest reasons this employee was flagged.

    `row`         - one employee's feature values (pandas Series or dict)
    `cohort`      - output of build_cohort_stats()
    `importances` - {feature: weight} from the trained model; optional
    `top_n`       - how many reasons to return
    """
    importances = importances or {}
    scored = []

    for feature, meta in FEATURE_META.items():
        if feature not in cohort:
            continue
        try:
            value = float(row[feature])
        except (KeyError, TypeError, ValueError):
            continue
        if np.isnan(value):
            continue

        base = cohort[feature]
        median, spread = base["median"], base["spread"]

        # Signed deviation in the "worse" direction.
        raw = (value - median) / spread
        dev = raw if meta["worse"] == "high" else -raw

        # Only surface genuinely unusual values, and demand a stronger signal
        # from contextual features.
        floor = 1.0 if feature in _WEAK_AS_REASON else 0.5
        if dev < floor:
            continue

        weight = float(importances.get(feature, 0.0))
        # Importance acts as a multiplier but never fully silences a large
        # deviation, so the explanation still works before the model is trained.
        contribution = dev * (0.35 + weight)

        # A ratio reads better than a z-score for non-technical users, but is
        # only meaningful when the baseline isn't ~zero.
        ratio = (value / median) if median > 1e-9 else None

        if meta["worse"] == "high" and ratio and ratio >= 1.3:
            detail = f"{ratio:.1f}x the company average"
        elif meta["worse"] == "low":
            detail = "below the company average"
        else:
            detail = "above the company average"

        scored.append({
            "feature":      feature,
            "label":        meta["label"],
            "value":        _fmt(value, meta),
            "baseline":     _fmt(median, meta),
            "detail":       detail,
            "severity":     _severity(dev),
            "deviation":    round(float(dev), 2),
            "importance":   round(weight, 4),
            "contribution": round(float(contribution), 4),
            "text":         f"{meta['label']} {detail} ({_fmt(value, meta)} vs {_fmt(median, meta)})",
        })

    scored.sort(key=lambda r: r["contribution"], reverse=True)
    return scored[:top_n]


def summarize(reasons: list[dict]) -> str:
    """One-line summary for emails, alert messages and table cells."""
    if not reasons:
        return "No single dominant factor - risk comes from a combination of signals."
    return "Flagged because: " + "; ".join(r["text"] for r in reasons)


# ============================================================================
# v2 (deterioration model) explanations
# ============================================================================
# The v2 features describe *direction*, so the phrasing differs: "rising by 6
# points since last quarter" is the actionable sentence, not "3x the average".

TREND_META = {
    "delta_taux_absence": {
        "label": "Absence trend",
        "kind": "delta_pct",
        "rising": "absence rate rising",
        "falling": "absence rate falling",
    },
    "ratio_absence": {
        "label": "Absence acceleration",
        "kind": "ratio",
    },
    "taux_absence_rec": {
        "label": "Absence rate (last 90 days)",
        "kind": "pct",
    },
    "nb_injust_rec": {
        "label": "Unjustified absences",
        "kind": "int",
    },
    "delta_taux_retard": {
        "label": "Lateness trend",
        "kind": "delta_pct",
        "rising": "lateness rising",
        "falling": "lateness falling",
    },
    "delta_heures": {
        "label": "Hours trend",
        "kind": "delta_hours",
    },
    "pct_absence_bord_rec": {
        "label": "Mon/Fri clustering",
        "kind": "pct",
    },
    "ecart_dept_absence": {
        "label": "vs department",
        "kind": "delta_pct",
        "rising": "above department norm",
        "falling": "below department norm",
    },
    "jours_depuis_absence": {
        "label": "Days since last absence",
        "kind": "days",
    },
}


def explain_trend_row(row, importances: dict | None = None, top_n: int = 3) -> list[dict]:
    """Human-readable drivers for a v2 (deterioration) prediction."""
    importances = importances or {}
    out = []

    def add(feature, text, value, severity, score):
        out.append({
            "feature": feature,
            "label": TREND_META.get(feature, {}).get("label", feature),
            "value": value,
            "text": text,
            "severity": severity,
            "contribution": round(float(score), 4),
            "importance": round(float(importances.get(feature, 0.0)), 4),
        })

    def g(k, default=0.0):
        try:
            v = float(row[k])
            return 0.0 if np.isnan(v) else v
        except (KeyError, TypeError, ValueError):
            return default

    w = lambda k: 0.35 + float(importances.get(k, 0.0))

    # Rising absence — the headline signal for this model.
    #
    # Threshold tuned during testing: a 90-day window on an employee who is
    # simply a *consistently* high absentee still drifts a few points from pure
    # randomness. Requiring both an absolute rise (>= 2 pts) AND a relative one
    # (>= 1.25x, unless the jump is large outright) stops normal variance being
    # narrated to HR as "deteriorating".
    d_abs = g("delta_taux_absence")
    ratio = g("ratio_absence", 1.0)
    if d_abs >= 0.02 and (ratio >= 1.25 or d_abs >= 0.05):
        pts = d_abs * 100
        sev = "high" if pts >= 8 else "medium" if pts >= 4 else "low"
        add("delta_taux_absence",
            f"Absence rate rising — up {pts:.1f} points vs the previous 90 days",
            f"+{pts:.1f} pts", sev, pts * w("delta_taux_absence"))

    # Unjustified absences carry more weight than justified ones.
    inj = g("nb_injust_rec")
    if inj >= 2:
        sev = "high" if inj >= 5 else "medium"
        add("nb_injust_rec",
            f"{int(inj)} unjustified absence{'s' if inj > 1 else ''} in the last 90 days",
            str(int(inj)), sev, inj * w("nb_injust_rec"))

    # Absence bunched against the weekend.
    edge = g("pct_absence_bord_rec")
    if edge >= 0.5 and g("nb_absences_rec") >= 3:
        add("pct_absence_bord_rec",
            f"{edge*100:.0f}% of absences fall on a Monday or Friday",
            f"{edge*100:.0f}%", "medium", edge * 4 * w("pct_absence_bord_rec"))

    # Department-relative context.
    ec = g("ecart_dept_absence")
    if ec >= 0.02:
        pts = ec * 100
        add("ecart_dept_absence",
            f"Absence rate {pts:.1f} points above their department's average",
            f"+{pts:.1f} pts", "medium" if pts < 5 else "high",
            pts * w("ecart_dept_absence"))

    # Falling hours often precedes disengagement.
    dh = g("delta_heures")
    if dh <= -0.4:
        add("delta_heures",
            f"Working {abs(dh):.1f}h/day less than the previous period",
            f"{dh:.1f} h", "medium", abs(dh) * 3 * w("delta_heures"))

    # Rising lateness.
    d_ret = g("delta_taux_retard")
    if d_ret >= 0.05:
        pts = d_ret * 100
        add("delta_taux_retard",
            f"Lateness rising — up {pts:.1f} points vs the previous 90 days",
            f"+{pts:.1f} pts", "medium", pts * 0.6 * w("delta_taux_retard"))

    out.sort(key=lambda r: r["contribution"], reverse=True)
    return out[:top_n]
