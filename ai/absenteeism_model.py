import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import precision_score, recall_score, f1_score, classification_report
import pickle
import os
from datetime import date
from sqlalchemy.orm import Session

from ai.preprocessor import get_employe_features, get_employe_features_periode
from ai.explainer import build_cohort_stats, explain_employee, summarize

MODEL_PATH   = "ai/models/absenteeism_model.pkl"
SCALER_PATH  = "ai/models/scaler.pkl"
METRICS_PATH = "ai/models/model_metrics.json"

FEATURE_LABELS = [
    "Seniority (months)", "Total absences", "Unjustified absences",
    "Late arrivals", "Leave days taken", "Avg hours/day",
    "Avg lateness (min)", "Absence rate (%)", "Late rate (%)",
]

FEATURES = [
    "anciennete",
    "nb_absences",
    "nb_absences_injust",
    "nb_retards",
    "nb_conges",
    "moy_heures_jour",
    "moy_retard_min",
    "taux_absence",
    "taux_retard",
]

# ──────────────────────────────────────────────
# Training periods for temporal validation
# ──────────────────────────────────────────────
TRAIN_DEBUT = date(2016, 1, 1)
TRAIN_FIN   = date(2023, 12, 31)
LABEL_DEBUT = date(2024, 1, 1)
LABEL_FIN   = date(2025, 12, 31)


def _rule_based_f1(X_raw: pd.DataFrame, y: pd.Series) -> float:
    """
    Baseline classifier: flag employee as at-risk when their absence rate
    is at or above the dataset 75th percentile - the simplest HR rule.
    Comparing RF against this baseline proves the model adds value beyond
    what a plain threshold already captures.
    """
    threshold = X_raw["taux_absence"].quantile(0.75)
    y_pred    = (X_raw["taux_absence"] >= threshold).astype(int)
    return round(f1_score(y, y_pred, zero_division=0) * 100, 2)


def _fit_and_evaluate(X: pd.DataFrame, y: pd.Series):
    """
    Fit a Random Forest and return (model, scaler, metrics).

    Metrics include:
    - Holdout accuracy / precision / recall / F1  (80-20 split)
    - 5-fold stratified cross-validation: mean ± std F1 and accuracy
    - Rule-based baseline F1 (threshold on absence rate)

    The cross-validation and baseline comparison directly address the
    question "does the ML model generalise beyond what the data generator
    already encodes?"  If RF CV-F1 >> baseline F1, the answer is yes.
    """
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    baseline_f1 = _rule_based_f1(X, y)

    if len(X) < 10:
        model = RandomForestClassifier(n_estimators=50, random_state=42)
        model.fit(X_scaled, y)
        return model, scaler, {
            "accuracy"    : round(model.score(X_scaled, y) * 100, 2),
            "precision"   : None, "recall": None, "f1": None,
            "baseline_f1" : baseline_f1,
            "note"        : "Dataset too small for train/test split - trained on all samples",
        }

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y if y.sum() > 1 else None
    )
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=4,
        min_samples_leaf=3,
        random_state=42,
    )
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metrics: dict = {
        "accuracy"    : round(model.score(X_test, y_test) * 100, 2),
        "precision"   : round(precision_score(y_test, y_pred, zero_division=0) * 100, 2),
        "recall"      : round(recall_score(y_test, y_pred, zero_division=0) * 100, 2),
        "f1"          : round(f1_score(y_test, y_pred, zero_division=0) * 100, 2),
        "baseline_f1" : baseline_f1,
        "report"      : classification_report(y_test, y_pred, zero_division=0),
    }

    # 5-fold stratified cross-validation (only when we have enough samples per class)
    if len(X) >= 25 and int(y.sum()) >= 5 and int((1 - y).sum()) >= 5:
        cv  = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        rf2 = RandomForestClassifier(n_estimators=100, max_depth=4, min_samples_leaf=3, random_state=42)
        cv_f1  = cross_val_score(rf2, X_scaled, y, cv=cv, scoring="f1",       n_jobs=1)
        cv_acc = cross_val_score(rf2, X_scaled, y, cv=cv, scoring="accuracy",  n_jobs=1)
        metrics["cv_f1_mean"]  = round(float(cv_f1.mean())  * 100, 2)
        metrics["cv_f1_std"]   = round(float(cv_f1.std())   * 100, 2)
        metrics["cv_acc_mean"] = round(float(cv_acc.mean()) * 100, 2)
        metrics["cv_acc_std"]  = round(float(cv_acc.std())  * 100, 2)

    return model, scaler, metrics


def entrainer_modele(db: Session):
    """
    Train the absenteeism risk model using temporal validation:

    - Features computed from historical period (2016-2023)
    - Labels derived from actual employee behaviour in 2024-2025
      (employees in the top 25 % by absence rate in 2024-2025 are labelled
      as high-risk)

    This avoids the circular labelling problem where labels are derived
    from the same data used as features.  The model genuinely predicts
    future risk from past patterns.

    Falls back to heuristic labelling on all-time data when either
    period lacks sufficient records.
    """
    os.makedirs("ai/models", exist_ok=True)

    df_train = get_employe_features_periode(db, TRAIN_DEBUT, TRAIN_FIN)
    df_label = get_employe_features_periode(db, LABEL_DEBUT, LABEL_FIN)

    use_temporal = (
        not df_train.empty
        and not df_label.empty
        and len(df_train) >= 10
        and len(df_label) >= 10
    )

    if use_temporal:
        # Build ground-truth labels from the label period
        p75 = df_label["taux_absence"].quantile(0.75)
        df_labels = df_label[["employe_id"]].copy()
        df_labels["a_risque"] = (df_label["taux_absence"] >= p75).astype(int)

        # Inner-join: only employees present in both periods
        df = df_train.merge(df_labels, on="employe_id")
        validation_method = "temporal (2016-2023 features -> 2024-2025 labels)"
    else:
        # Fallback: heuristic labelling on all-time data
        df = get_employe_features(db)
        if df.empty or len(df) < 5:
            return {"error": "Not enough data to train model"}

        p75_abs   = df["nb_absences"].quantile(0.75)
        p75_injust= df["nb_absences_injust"].quantile(0.75)
        p75_taux  = df["taux_absence"].quantile(0.75)
        p75_heures= df["moy_heures_jour"].quantile(0.25)   # low hours = risk

        df["a_risque"] = (
            (df["nb_absences"]       >= p75_abs).astype(int)
          + (df["nb_absences_injust"] >= p75_injust).astype(int)
          + (df["taux_absence"]       >= p75_taux).astype(int)
          + (df["moy_heures_jour"]    <= p75_heures).astype(int)
        ) >= 2
        df["a_risque"] = df["a_risque"].astype(int)
        validation_method = "heuristic (all-time data, fallback)"

    X = df[FEATURES].fillna(0)
    y = df["a_risque"]

    model, scaler, metrics = _fit_and_evaluate(X, y)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

    feature_importance = [
        {"feature": label, "importance": round(float(imp) * 100, 1)}
        for label, imp in zip(FEATURE_LABELS, model.feature_importances_)
    ]
    feature_importance.sort(key=lambda x: x["importance"], reverse=True)

    import json
    from datetime import datetime as dt
    model_info = {
        "trained_at"        : dt.now().isoformat(timespec="seconds"),
        "validation_method" : validation_method,
        "nb_employes"       : len(df),
        "nb_a_risque"       : int(y.sum()),
        # Holdout metrics
        "accuracy"          : metrics.get("accuracy"),
        "precision"         : metrics.get("precision"),
        "recall"            : metrics.get("recall"),
        "f1"                : metrics.get("f1"),
        # Cross-validation (absent when dataset too small)
        "cv_f1_mean"        : metrics.get("cv_f1_mean"),
        "cv_f1_std"         : metrics.get("cv_f1_std"),
        "cv_acc_mean"       : metrics.get("cv_acc_mean"),
        "cv_acc_std"        : metrics.get("cv_acc_std"),
        # Baseline comparison
        "baseline_f1"       : metrics.get("baseline_f1"),
        "feature_importance": feature_importance,
    }
    with open(METRICS_PATH, "w") as f:
        json.dump(model_info, f, indent=2)

    return {"status": "success", "features_used": FEATURES, **metrics,
            "validation_method": validation_method, "nb_employes": len(df), "nb_a_risque": int(y.sum())}


def predire_absenteisme(db: Session, use_v2: bool = True):
    """Predict absenteeism risk for all active employees.

    Prefers the v2 deterioration model (ai/risk_model.py) when a trained one is
    on disk, falling back to the legacy level-based model, then to the
    rule-based scorer. Callers keep the same result shape either way.

    NOTE: this used to delete the model files and retrain on *every* call -
    including every dashboard load - which made the weekly scheduled retrain
    pointless and would crawl on a real client's data. Training now happens only
    via the scheduler or an explicit request; prediction just loads the cache.
    """
    if use_v2:
        try:
            from ai.risk_model import predict_risk, model_available, load_metrics
            from ai.explainer import explain_trend_row, summarize
            from ai.trend_features import build_trend_features, TREND_FEATURES
            if model_available():
                rows = predict_risk(db)
                if rows:
                    metrics = load_metrics()
                    imp = {}
                    try:
                        from ai.trend_features import TREND_LABELS
                        lbl2feat = dict(zip(TREND_LABELS, TREND_FEATURES))
                        for item in metrics.get("feature_importance", []):
                            f = lbl2feat.get(item.get("feature"))
                            if f:
                                imp[f] = item.get("importance", 0) / 100.0
                    except Exception:
                        pass
                    feats = build_trend_features(db, __import__("datetime").date.today())
                    by_id = {int(r["employe_id"]): r for _, r in feats.iterrows()} if not feats.empty else {}
                    for row in rows:
                        frow = by_id.get(row["employe_id"])
                        reasons = explain_trend_row(frow, imp) if frow is not None else []
                        row["raisons"] = reasons
                        row["explication"] = summarize(reasons)
                    return rows
        except Exception:
            pass  # any v2 problem falls through to the legacy path

    # ── Legacy path (level-based model) ──────────────────────────────
    if not (os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH)):
        result = entrainer_modele(db)
        if "error" in result:
            return predire_sans_modele(db)

    try:
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        with open(SCALER_PATH, "rb") as f:
            scaler = pickle.load(f)
    except Exception:
        return predire_sans_modele(db)

    df = get_employe_features(db)
    if df.empty:
        return []

    X        = df[FEATURES].fillna(0)
    X_scaled = scaler.transform(X)

    probabilites = model.predict_proba(X_scaled)[:, 1]
    df["probabilite"] = probabilites

    threshold = df["probabilite"].quantile(0.75)
    a_risque  = df[df["probabilite"] >= threshold].copy()
    a_risque  = a_risque.sort_values("probabilite", ascending=False)

    # Explainability: baselines are computed on the FULL cohort (not just the
    # at-risk subset) so "vs company average" compares against everyone.
    cohort      = build_cohort_stats(df, FEATURES)
    importances = dict(zip(FEATURES, model.feature_importances_))

    resultats = []
    for _, row in a_risque.iterrows():
        proba   = round(float(row["probabilite"]) * 100, 1)
        niveau  = "Critique" if proba > 70 else "Moyen"
        reasons = explain_employee(row, cohort, importances)
        resultats.append({
            "employe_id"  : int(row["employe_id"]),
            "nom"         : row["nom"],
            "probabilite" : proba,
            "niveau"      : niveau,
            "taux_absence": round(float(row["taux_absence"]) * 100, 1),
            "nb_absences" : int(row["nb_absences"]),
            "nb_retards"  : int(row["nb_retards"]),
            "raisons"     : reasons,
            "explication" : summarize(reasons),
        })

    return resultats


def predire_sans_modele(db: Session):
    """Score-based fallback when model is unavailable."""
    df = get_employe_features(db)
    if df.empty:
        return []

    cohort  = build_cohort_stats(df, FEATURES)
    p75_abs = df["nb_absences"].quantile(0.75)
    p75_inj = df["nb_absences_injust"].quantile(0.75)
    p90_abs = df["nb_absences"].quantile(0.90)

    resultats = []
    for _, row in df.iterrows():
        score = 0
        if row["nb_absences"] >= p90_abs:
            score += 50
        elif row["nb_absences"] >= p75_abs:
            score += 30
        if row["nb_absences_injust"] >= p75_inj:
            score += 25
        if row["moy_heures_jour"] < 7.0:
            score += 15
        if row["taux_absence"] > df["taux_absence"].quantile(0.80):
            score += 10

        if score >= 30:
            niveau  = "Critique" if score >= 60 else "Moyen"
            reasons = explain_employee(row, cohort, None)
            resultats.append({
                "employe_id"  : int(row["employe_id"]),
                "nom"         : row["nom"],
                "probabilite" : float(min(score, 95)),
                "niveau"      : niveau,
                "taux_absence": round(float(row["taux_absence"]) * 100, 1),
                "nb_absences" : int(row["nb_absences"]),
                "nb_retards"  : int(row["nb_retards"]),
                "raisons"     : reasons,
                "explication" : summarize(reasons),
            })

    return sorted(resultats, key=lambda x: x["probabilite"], reverse=True)
