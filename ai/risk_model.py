"""Absenteeism risk model v2 — predicts *deterioration*, not level.

What changed and why
--------------------
The earlier model predicted "will this employee have a high absence rate", using cumulative
all-time features. Its metrics showed the problem:

    rule-based baseline F1 : 73.7
    Random Forest CV F1    : 67.4  (+/- 20.0)

The model lost to a one-line percentile rule, because the label ("high absence
rate later") and the features ("high absence rate earlier") were two views of
the same quantity. There was no headroom.

v2 makes four changes:

1. **Target = deterioration.** Label is whether an employee's absence rate rises
   materially over the next horizon, relative to their own recent baseline. A
   percentile threshold on the current rate structurally cannot answer this, so
   beating the baseline now means something.

2. **Many snapshots instead of one.** Features are rebuilt at reference dates
   rolling through history, so 76 employees become thousands of training rows.
   This is what fixes the +/-20 F1 variance: v1 was cross-validating on ~60 rows.

3. **Temporal split by snapshot date.** Early snapshots train, later ones test.
   No employee's future leaks into their own training row.

4. **Calibrated probabilities.** A Random Forest's raw `predict_proba` is not a
   real probability; the UI displays it as a percentage people will act on, so
   it is wrapped in isotonic/sigmoid calibration.

The rule-based baseline is retained and evaluated on the identical test set —
if v2 cannot beat it, that must stay visible rather than be quietly dropped.
"""
from __future__ import annotations

import json
import os
import pickle
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from ai.trend_features import (
    TREND_FEATURES, TREND_LABELS,
    build_deterioration_dataset, build_trend_features,
)

MODEL_V2_PATH   = "ai/models/risk_model_v2.pkl"
SCALER_V2_PATH  = "ai/models/risk_scaler_v2.pkl"
METRICS_V2_PATH = "ai/models/risk_metrics_v2.json"

WINDOW_DAYS  = 90     # length of the recent / prior observation windows
HORIZON_DAYS = 90     # how far ahead we predict
MIN_HAUSSE   = 0.03   # +3 percentage points of absence rate = "deterioration"
SNAPSHOT_STEP = 45    # days between reference dates


# ─────────────────────────────────────────────────────────────
# Dataset assembly
# ─────────────────────────────────────────────────────────────
def build_panel(
    db: Session,
    start: date,
    end: date,
    step_days: int = SNAPSHOT_STEP,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Stack snapshots across history into one panel dataset.

    Returns (X, y, snapshot_date) — the dates are kept so the split can be
    temporal rather than random.
    """
    frames, labels, stamps = [], [], []
    ref = start
    while ref <= end:
        X, y = build_deterioration_dataset(
            db, ref, WINDOW_DAYS, HORIZON_DAYS, MIN_HAUSSE
        )
        if not X.empty and len(y) == len(X):
            frames.append(X)
            labels.append(y)
            stamps.append(pd.Series([ref] * len(X)))
        ref += timedelta(days=step_days)

    if not frames:
        return pd.DataFrame(), pd.Series(dtype=int), pd.Series(dtype="object")

    return (
        pd.concat(frames, ignore_index=True),
        pd.concat(labels, ignore_index=True),
        pd.concat(stamps, ignore_index=True),
    )


def _baseline_predictions(X: pd.DataFrame, quantile: float = 0.75) -> np.ndarray:
    """The rule v2 must beat: flag whoever currently has the highest absence rate.

    This is v1's logic in one line. Evaluated on the same test set, it answers
    "does the model add anything a threshold could not?"
    """
    if X.empty:
        return np.array([])
    thr = X["taux_absence_rec"].quantile(quantile)
    return (X["taux_absence_rec"] >= thr).astype(int).to_numpy()


# ─────────────────────────────────────────────────────────────
# Training
# ─────────────────────────────────────────────────────────────
def train_risk_model(
    db: Session,
    start: date | None = None,
    end: date | None = None,
) -> dict:
    """Train, calibrate, evaluate against the baseline, and persist."""
    today = date.today()
    start = start or date(today.year - 6, 1, 1)
    # leave room for the label horizon at the end of history
    end = end or (today - timedelta(days=HORIZON_DAYS + 5))

    X_all, y_all, stamps = build_panel(db, start, end)
    if X_all.empty or len(X_all) < 60:
        return {"status": "error", "error": "not enough history to train v2",
                "rows": int(len(X_all))}
    if y_all.nunique() < 2:
        return {"status": "error", "error": "only one class present in labels",
                "rows": int(len(X_all))}

    # Temporal split: the last 25% of snapshot dates become the test set.
    uniq = sorted(stamps.unique())
    if len(uniq) < 4:
        return {"status": "error", "error": "not enough distinct snapshots"}
    cut = uniq[int(len(uniq) * 0.75)]
    tr, te = stamps < cut, stamps >= cut

    Xtr, ytr = X_all.loc[tr, TREND_FEATURES].fillna(0), y_all[tr]
    Xte, yte = X_all.loc[te, TREND_FEATURES].fillna(0), y_all[te]

    if len(Xte) < 15 or ytr.nunique() < 2 or yte.nunique() < 2:
        return {"status": "error", "error": "temporal split left an unusable fold"}

    scaler = StandardScaler().fit(Xtr)
    Xtr_s, Xte_s = scaler.transform(Xtr), scaler.transform(Xte)

    base = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=8,
        class_weight="balanced",   # deterioration is the minority class
        random_state=42,
        n_jobs=-1,
    )
    # Calibrate so the displayed percentage means what it says.
    method = "isotonic" if len(Xtr) >= 500 else "sigmoid"
    model = CalibratedClassifierCV(base, method=method, cv=3)
    model.fit(Xtr_s, ytr)

    proba = model.predict_proba(Xte_s)[:, 1]
    pred = (proba >= 0.5).astype(int)

    # Baseline on the identical test rows.
    base_pred = _baseline_predictions(X_all.loc[te])

    try:
        auc = round(float(roc_auc_score(yte, proba)) * 100, 2)
    except ValueError:
        auc = None

    # Feature importance comes from the underlying forest (calibration wraps it).
    base.fit(Xtr_s, ytr)
    importances = [
        {"feature": lbl, "importance": round(float(v) * 100, 1)}
        for lbl, v in sorted(zip(TREND_LABELS, base.feature_importances_),
                             key=lambda t: t[1], reverse=True)
    ]

    metrics = {
        "trained_at": pd.Timestamp.now().isoformat(timespec="seconds"),
        "version": "v2-deterioration",
        "target": (f"absence rate rises >= {MIN_HAUSSE*100:.0f} pts over the next "
                   f"{HORIZON_DAYS} days vs the employee's own prior {WINDOW_DAYS} days"),
        "validation_method": "temporal split across rolling snapshots (last 25% of dates held out)",
        "calibration": method,
        "n_rows_total": int(len(X_all)),
        "n_rows_train": int(len(Xtr)),
        "n_rows_test": int(len(Xte)),
        "n_snapshots": int(len(uniq)),
        "positive_rate": round(float(y_all.mean()) * 100, 1),
        "accuracy":  round(float(accuracy_score(yte, pred)) * 100, 2),
        "precision": round(float(precision_score(yte, pred, zero_division=0)) * 100, 2),
        "recall":    round(float(recall_score(yte, pred, zero_division=0)) * 100, 2),
        "f1":        round(float(f1_score(yte, pred, zero_division=0)) * 100, 2),
        "roc_auc":   auc,
        "baseline_f1": round(float(f1_score(yte, base_pred, zero_division=0)) * 100, 2),
        "baseline_precision": round(float(precision_score(yte, base_pred, zero_division=0)) * 100, 2),
        "feature_importance": importances,
    }
    metrics["beats_baseline"] = metrics["f1"] > metrics["baseline_f1"]
    metrics["uplift_f1"] = round(metrics["f1"] - metrics["baseline_f1"], 2)

    os.makedirs("ai/models", exist_ok=True)
    with open(MODEL_V2_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(SCALER_V2_PATH, "wb") as f:
        pickle.dump(scaler, f)
    with open(METRICS_V2_PATH, "w") as f:
        json.dump(metrics, f, indent=2)

    return {"status": "success", **metrics}


# ─────────────────────────────────────────────────────────────
# Prediction (cached — no retraining per request)
# ─────────────────────────────────────────────────────────────
def model_available() -> bool:
    return os.path.exists(MODEL_V2_PATH) and os.path.exists(SCALER_V2_PATH)


def load_metrics() -> dict:
    if not os.path.exists(METRICS_V2_PATH):
        return {}
    try:
        with open(METRICS_V2_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def predict_risk(
    db: Session,
    seuil: float = 0.50,
    ref_date: date | None = None,
) -> list[dict]:
    """Score every active employee for *rising* absenteeism risk.

    Uses the cached model — training happens on the scheduler, not on every
    dashboard load. Returns an absolute-threshold list: if nobody is
    deteriorating, the list is legitimately empty (v1 always flagged the top
    25%, even in a perfectly healthy company).
    """
    if not model_available():
        return []

    ref_date = ref_date or date.today()
    X = build_trend_features(db, ref_date, WINDOW_DAYS)
    if X.empty:
        return []

    try:
        with open(MODEL_V2_PATH, "rb") as f:
            model = pickle.load(f)
        with open(SCALER_V2_PATH, "rb") as f:
            scaler = pickle.load(f)
        proba = model.predict_proba(scaler.transform(X[TREND_FEATURES].fillna(0)))[:, 1]
    except Exception:
        return []

    X = X.copy()
    X["probabilite"] = proba
    flagged = X[X["probabilite"] >= seuil].sort_values("probabilite", ascending=False)

    out = []
    for _, r in flagged.iterrows():
        p = round(float(r["probabilite"]) * 100, 1)
        out.append({
            "employe_id":   int(r["employe_id"]),
            "nom":          str(r.get("nom_complet", "")).strip(),
            "probabilite":  p,
            "niveau":       "Critique" if p >= 70 else "Moyen",
            "taux_absence": round(float(r["taux_absence_rec"]) * 100, 1),
            "nb_absences":  int(r["nb_absences_rec"]),
            "nb_retards":   int(r["nb_retards_rec"]),
            "tendance":     round(float(r["delta_taux_absence"]) * 100, 1),
            "model_version": "v2-deterioration",
        })
    return out
