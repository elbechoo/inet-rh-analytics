"""Benchmark on the UCI 'Absenteeism at Work' dataset.

Real data - a Brazilian courier company, 2007-2010, 740 absence records across
36 employees. Published and independent, so a result here is not a restatement
of assumptions baked into our own simulator.

    python -m ai.benchmark_uci --file Absenteeism_at_work.csv

Task
----
Given what is known when an employee calls in - the stated reason, the day,
the season, their tenure, commute, workload - will this absence cost a full
working day or more (>= 8 hours)? Roughly 37% of records do, so the classes are
reasonably balanced and accuracy is not trivially gamed.

Why grouped cross-validation
----------------------------
Absences are wildly unevenly distributed: one employee accounts for 113 of the
740 rows, another for a single one. Split those rows at random and the same
person lands in both train and test, so the model learns *that individual's*
habits and scores brilliantly on them. It looks like prediction; it is
recall.

Splitting by employee instead means every person in the test set is someone the
model has never seen - which is the situation it actually faces in production,
when HR asks about a new hire. This script reports both so the gap is visible,
because that gap is the honest measure of how much of a score is memorisation.
"""
import argparse
import csv
import sys

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupKFold, StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

TARGET_HOURS = 8          # a full working day or more
N_SPLITS = 5

# Everything an HR system plausibly knows at the moment of the call.
FEATURES = [
    "Reason for absence", "Month of absence", "Day of the week", "Seasons",
    "Transportation expense", "Distance from Residence to Work", "Service time",
    "Age", "Work load Average/day", "Hit target", "Disciplinary failure",
    "Education", "Son", "Social drinker", "Social smoker", "Pet",
    "Body mass index",
]


def load(path: str) -> pd.DataFrame:
    """The UCI file ships semicolon-delimited; some mirrors use commas."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        sample = f.read(2048)
    delim = ";" if sample.count(";") > sample.count(",") else ","
    df = pd.read_csv(path, delimiter=delim)
    df.columns = [c.strip() for c in df.columns]
    return df


def rule_baseline(X: pd.DataFrame) -> np.ndarray:
    """The rule an HR manager would use without any model.

    Reasons 1-14 are ICD medical diagnoses - genuine illness, which tends to
    take a person out for a full day. Reasons 15+ are administrative or routine
    (dental, physiotherapy, consultation) and usually cost a few hours.
    Anything logged as a disciplinary failure is recorded as zero hours.
    """
    reason = X["Reason for absence"].to_numpy()
    disciplinary = X["Disciplinary failure"].to_numpy()
    pred = ((reason >= 1) & (reason <= 14)).astype(int)
    pred[disciplinary == 1] = 0
    return pred


def evaluate(name, model, X, y, groups, strategy: str) -> dict:
    """Cross-validate, either grouped by employee or shuffled at random."""
    if strategy == "grouped":
        splitter = GroupKFold(n_splits=N_SPLITS)
        folds = splitter.split(X, y, groups)
    else:
        splitter = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=42)
        folds = splitter.split(X, y)

    f1s, precs, recs, aucs = [], [], [], []
    for tr, te in folds:
        Xtr, Xte = X.iloc[tr], X.iloc[te]
        ytr, yte = y.iloc[tr], y.iloc[te]

        if model == "rule":
            pred = rule_baseline(Xte)
            proba = pred.astype(float)
        else:
            m = model()
            m.fit(Xtr, ytr)
            pred = m.predict(Xte)
            proba = m.predict_proba(Xte)[:, 1] if hasattr(m, "predict_proba") else pred

        f1s.append(f1_score(yte, pred, zero_division=0))
        precs.append(precision_score(yte, pred, zero_division=0))
        recs.append(recall_score(yte, pred, zero_division=0))
        try:
            aucs.append(roc_auc_score(yte, proba))
        except ValueError:
            pass

    return {
        "name": name,
        "f1": np.mean(f1s) * 100,
        "f1_std": np.std(f1s) * 100,
        "precision": np.mean(precs) * 100,
        "recall": np.mean(recs) * 100,
        "auc": (np.mean(aucs) * 100) if aucs else float("nan"),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Benchmark on real UCI absenteeism data")
    ap.add_argument("--file", default="Absenteeism_at_work.csv")
    args = ap.parse_args()

    try:
        df = load(args.file)
    except FileNotFoundError:
        sys.exit(f"Not found: {args.file}\n"
                 "Download from https://archive.ics.uci.edu/dataset/445/absenteeism+at+work")

    missing = [c for c in FEATURES + ["ID", "Absenteeism time in hours"] if c not in df.columns]
    if missing:
        sys.exit(f"Missing columns: {missing}")

    X = df[FEATURES].astype(float)
    y = (df["Absenteeism time in hours"] >= TARGET_HOURS).astype(int)
    groups = df["ID"]

    print(f"UCI Absenteeism at Work - {len(df)} records, {groups.nunique()} employees")
    print(f"Target: absence >= {TARGET_HOURS}h    positives: {y.sum()} ({y.mean()*100:.1f}%)")
    print(f"Records per employee: min {groups.value_counts().min()}, "
          f"max {groups.value_counts().max()}\n")

    candidates = [
        ("Majority class", lambda: DummyClassifier(strategy="most_frequent")),
        ("Rule (medical reason)", "rule"),
        ("Logistic regression", lambda: make_pipeline(StandardScaler(),
                                                      LogisticRegression(max_iter=2000))),
        ("Random forest", lambda: RandomForestClassifier(
            n_estimators=400, min_samples_leaf=3, random_state=42, n_jobs=-1)),
        ("Gradient boosting", lambda: GradientBoostingClassifier(random_state=42)),
    ]

    for strategy, blurb in [
        ("grouped", "GROUPED BY EMPLOYEE - every test employee is unseen (honest)"),
        ("random", "RANDOM SPLIT - same employees in train and test (leaky)"),
    ]:
        print("=" * 74)
        print(blurb)
        print("=" * 74)
        print(f"  {'model':<24} {'F1':>13} {'prec':>7} {'recall':>7} {'AUC':>7}")
        results = []
        for name, model in candidates:
            r = evaluate(name, model, X, y, groups, strategy)
            results.append(r)
            print(f"  {r['name']:<24} {r['f1']:>6.1f} ± {r['f1_std']:>4.1f} "
                  f"{r['precision']:>7.1f} {r['recall']:>7.1f} {r['auc']:>7.1f}")

        best_rule = max(r["f1"] for r in results[:2])
        best_ml = max(r["f1"] for r in results[2:])
        gap = best_ml - best_rule
        verdict = "beats" if gap > 0 else "does NOT beat"
        print(f"\n  best ML {verdict} the best rule by {gap:+.1f} F1 points\n")

    print("=" * 74)
    print("Read the two tables together. The random split is the number most\n"
          "projects report; the grouped split is the number that survives contact\n"
          "with an employee the model has never seen. The difference between them\n"
          "is how much of the score was memorising individuals.")


if __name__ == "__main__":
    main()
