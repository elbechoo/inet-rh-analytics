"""Windowed / trend features for absenteeism modelling.

Why this module exists
----------------------
The original feature set was cumulative and all-time (total absences, overall
absence rate). A model trained on it can only learn "this person has been absent
a lot", which a single percentile rule already expresses - which is why the
Random Forest did not beat the rule-based baseline (CV F1 67.4 vs baseline 73.7).

To add value the model has to answer a question a static threshold cannot:
**who is getting worse?** That requires comparing an employee against their own
recent past, so every feature here is windowed:

    prior window            recent window           (future = label horizon)
    [ref-2w , ref-w)        [ref-w , ref)           [ref , ref+h)

Deltas between the prior and recent windows capture deterioration; a percentile
on the current level cannot.

Performance note: all rows are fetched in two bulk queries and grouped in
pandas, instead of the previous two queries *per employee* (an N+1 pattern that
would crawl on a real client's database).
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from models.models import Employe, Pointage, Absence

EPS = 1e-9


def _load_frames(db: Session, start: date, end: date):
    """Two bulk queries covering the whole span we need."""
    pointages = db.query(
        Pointage.employe_id, Pointage.date_pointage,
        Pointage.statut, Pointage.duree_travail, Pointage.retard_minutes,
    ).filter(
        Pointage.date_pointage >= start, Pointage.date_pointage <= end
    ).all()

    absences = db.query(
        Absence.employe_id, Absence.date_absence, Absence.justifiee,
    ).filter(
        Absence.date_absence >= start, Absence.date_absence <= end
    ).all()

    p = pd.DataFrame(pointages, columns=["employe_id", "d", "statut", "duree", "retard"])
    a = pd.DataFrame(absences, columns=["employe_id", "d", "justifiee"])
    for f in (p, a):
        if not f.empty:
            f["d"] = pd.to_datetime(f["d"])
    return p, a


def _window_stats(p: pd.DataFrame, a: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    """Per-employee behaviour inside one window."""
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    pw = p[(p["d"] >= s) & (p["d"] < e)] if not p.empty else p
    aw = a[(a["d"] >= s) & (a["d"] < e)] if not a.empty else a

    ids = set(pw["employe_id"].unique() if not pw.empty else []) | \
          set(aw["employe_id"].unique() if not aw.empty else [])
    if not ids:
        return pd.DataFrame(columns=["employe_id"])

    rows = []
    pg = pw.groupby("employe_id") if not pw.empty else None
    ag = aw.groupby("employe_id") if not aw.empty else None

    for eid in ids:
        pe = pg.get_group(eid) if pg is not None and eid in pg.groups else pd.DataFrame(columns=pw.columns)
        ae = ag.get_group(eid) if ag is not None and eid in ag.groups else pd.DataFrame(columns=aw.columns)

        n_p = len(pe)
        n_a = len(ae)
        n_days = max(n_p + n_a, 1)
        n_ret = int((pe["statut"] == "En retard").sum()) if n_p else 0
        n_inj = int((~ae["justifiee"].fillna(False).astype(bool)).sum()) if n_a else 0

        # Monday/Friday absence clustering: absences bunched around the weekend
        # are a classic signal of discretionary rather than medical absence.
        if n_a:
            wd = ae["d"].dt.weekday
            n_edge = int(((wd == 0) | (wd == 4)).sum())
        else:
            n_edge = 0

        rows.append({
            "employe_id":     eid,
            "n_jours":        n_days,
            "nb_absences":    n_a,
            "nb_injust":      n_inj,
            "nb_retards":     n_ret,
            "taux_absence":   n_a / n_days,
            "taux_retard":    n_ret / max(n_p, 1),
            "moy_heures":     float(pe["duree"].fillna(0).mean()) if n_p else 0.0,
            "moy_retard_min": float(pe["retard"].fillna(0).mean()) if n_p else 0.0,
            "pct_absence_bord": n_edge / max(n_a, 1),
            "derniere_absence": ae["d"].max() if n_a else pd.NaT,
        })
    return pd.DataFrame(rows)


def build_trend_features(
    db: Session,
    ref_date: date,
    window_days: int = 90,
    min_activite: int = 10,
) -> pd.DataFrame:
    """Features describing an employee's behaviour *and its direction* at ref_date.

    Returns one row per employee with enough activity in the recent window.
    """
    prior_start  = ref_date - timedelta(days=window_days * 2)
    recent_start = ref_date - timedelta(days=window_days)

    p, a = _load_frames(db, prior_start, ref_date)
    if p.empty and a.empty:
        return pd.DataFrame()

    recent = _window_stats(p, a, recent_start, ref_date)
    prior  = _window_stats(p, a, prior_start, recent_start)
    if recent.empty:
        return pd.DataFrame()

    recent = recent[recent["n_jours"] >= min_activite]
    if recent.empty:
        return pd.DataFrame()

    df = recent.merge(prior, on="employe_id", how="left", suffixes=("_rec", "_pri"))

    # Employees absent from the prior window get neutral (not zero) baselines,
    # so a newcomer isn't misread as a dramatic deterioration.
    for col in ["taux_absence", "taux_retard", "moy_heures", "moy_retard_min"]:
        df[f"{col}_pri"] = df[f"{col}_pri"].fillna(df[f"{col}_rec"])
    for col in ["nb_absences", "nb_injust", "nb_retards"]:
        df[f"{col}_pri"] = df[f"{col}_pri"].fillna(0)

    # ── Trend features: the whole point of this module ──────────────────
    df["delta_taux_absence"] = df["taux_absence_rec"] - df["taux_absence_pri"]
    df["delta_taux_retard"]  = df["taux_retard_rec"]  - df["taux_retard_pri"]
    df["delta_heures"]       = df["moy_heures_rec"]   - df["moy_heures_pri"]
    df["ratio_absence"]      = df["taux_absence_rec"] / (df["taux_absence_pri"] + EPS)
    df["ratio_absence"]      = df["ratio_absence"].clip(0, 10)

    # Recency: a long gap since the last absence is protective.
    ref_ts = pd.Timestamp(ref_date)
    df["jours_depuis_absence"] = (ref_ts - df["derniere_absence_rec"]).dt.days
    df["jours_depuis_absence"] = df["jours_depuis_absence"].fillna(window_days * 2)

    # ── Department-relative context ─────────────────────────────────────
    # Absence norms differ hugely between a call centre and an accounts team;
    # comparing an employee to their own department is fairer than to the company.
    emp_rows = db.query(Employe.employe_id, Employe.departement_id, Employe.date_embauche,
                        Employe.prenom, Employe.nom, Employe.matricule).all()
    emps = pd.DataFrame(emp_rows, columns=["employe_id", "departement_id", "date_embauche",
                                           "prenom", "nom", "matricule"])
    df = df.merge(emps, on="employe_id", how="left")

    dept_mean = df.groupby("departement_id")["taux_absence_rec"].transform("mean")
    df["ecart_dept_absence"] = df["taux_absence_rec"] - dept_mean

    df["anciennete"] = df["date_embauche"].apply(
        lambda d: (ref_date - d).days / 365 if pd.notna(d) and d is not None else 0.0
    )
    df["nom_complet"] = df["prenom"].fillna("") + " " + df["nom"].fillna("")

    return df.reset_index(drop=True)


# Feature columns fed to the model, and their human labels.
TREND_FEATURES = [
    "taux_absence_rec",
    "delta_taux_absence",
    "ratio_absence",
    "nb_injust_rec",
    "taux_retard_rec",
    "delta_taux_retard",
    "moy_heures_rec",
    "delta_heures",
    "jours_depuis_absence",
    "pct_absence_bord_rec",
    "ecart_dept_absence",
    "anciennete",
]

TREND_LABELS = [
    "Absence rate (recent)",
    "Absence rate trend",
    "Absence rate ratio vs prior",
    "Unjustified absences (recent)",
    "Lateness rate (recent)",
    "Lateness trend",
    "Avg hours/day (recent)",
    "Hours trend",
    "Days since last absence",
    "Mon/Fri absence clustering",
    "Vs department average",
    "Seniority (years)",
]


def build_deterioration_dataset(
    db: Session,
    ref_date: date,
    window_days: int = 90,
    horizon_days: int = 90,
    min_hausse: float = 0.03,
):
    """X = behaviour up to ref_date, y = did absence get materially worse after it.

    The label deliberately measures *change*, not level: an employee already at a
    high but stable rate is not "deteriorating", while a reliable employee sliding
    downwards is exactly who HR wants to catch early - and precisely what a
    percentile threshold on the current rate cannot surface.
    """
    X = build_trend_features(db, ref_date, window_days)
    if X.empty:
        return pd.DataFrame(), pd.Series(dtype=int)

    future_end = ref_date + timedelta(days=horizon_days)
    p, a = _load_frames(db, ref_date, future_end)
    future = _window_stats(p, a, ref_date, future_end)
    if future.empty:
        return pd.DataFrame(), pd.Series(dtype=int)

    fut = future[["employe_id", "taux_absence", "n_jours"]].rename(
        columns={"taux_absence": "taux_absence_fut", "n_jours": "n_jours_fut"}
    )
    d = X.merge(fut, on="employe_id", how="inner")
    d = d[d["n_jours_fut"] >= 5]          # need enough future activity to judge
    if d.empty:
        return pd.DataFrame(), pd.Series(dtype=int)

    hausse = d["taux_absence_fut"] - d["taux_absence_rec"]
    y = (hausse >= min_hausse).astype(int)
    return d.reset_index(drop=True), y.reset_index(drop=True)
