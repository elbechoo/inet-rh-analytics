"""Model selection gate — decides whether the ML model is used at all.

A model trained on one company's data is not automatically useful on another's.
A client with three years of history and varied attendance behaviour may get a
genuinely predictive model; a client with sixty employees and eight months of
data almost certainly will not, and a forest fitted to that will look confident
while being noise.

So the model does not get to assume it is worth using. Every training run is
scored against a rule-based baseline on a held-out temporal split, and the
model is only promoted to serving if it beats that baseline by a real margin.
Otherwise the baseline serves, and the system says so.

This is what makes the pipeline portable: the same code adapts to whatever data
a deployment actually has, instead of assuming the shape of the dataset it was
originally written against.

    from ai.model_gate import train_and_gate, predict, active_strategy

    train_and_gate(db)          # trains, compares, promotes or rejects
    active_strategy()           # "model" | "baseline" | "insufficient_data"
    predict(db)                 # routes to whichever is active
"""
import json
import os
from datetime import date

from sqlalchemy.orm import Session

GATE_PATH = "ai/models/model_gate.json"

# ── Promotion thresholds ────────────────────────────────────
# Beating the baseline by a hair is not evidence of anything: with a small test
# set the difference is inside the noise. The model must win by a margin before
# it is trusted with a decision that affects how someone is managed.
MIN_UPLIFT_F1 = 5.0     # percentage points of F1 over the baseline
MIN_F1        = 40.0    # below this the model is not useful regardless

# ── Data sufficiency ────────────────────────────────────────
# Floors, not targets. Under these the question is not "is the model good" but
# "is there enough data to answer that question at all".
MIN_EMPLOYEES      = 30
MIN_POSITIVES      = 25     # minimum deterioration cases in the training panel
MIN_SNAPSHOT_ROWS  = 200    # total employee-snapshots in the panel


def _write_gate(payload: dict) -> None:
    os.makedirs(os.path.dirname(GATE_PATH), exist_ok=True)
    payload["decided_at"] = date.today().isoformat()
    with open(GATE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def read_gate() -> dict:
    if not os.path.exists(GATE_PATH):
        return {"strategy": "baseline", "reason": "never trained"}
    try:
        with open(GATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"strategy": "baseline", "reason": "gate file unreadable"}


def active_strategy() -> str:
    """Which predictor is currently serving: 'model' or 'baseline'."""
    return read_gate().get("strategy", "baseline")


def check_data_sufficiency(db: Session) -> dict:
    """Is there enough history here to evaluate a model honestly?"""
    from models.models import Employe, Pointage

    n_emp = db.query(Employe).filter(Employe.statut == "Actif").count()

    span_days = 0
    first = db.query(Pointage.date_pointage).order_by(Pointage.date_pointage.asc()).first()
    last = db.query(Pointage.date_pointage).order_by(Pointage.date_pointage.desc()).first()
    if first and last and first[0] and last[0]:
        span_days = (last[0] - first[0]).days

    reasons = []
    if n_emp < MIN_EMPLOYEES:
        reasons.append(f"only {n_emp} active employees (need {MIN_EMPLOYEES})")
    # Two observation windows plus a prediction horizon, and then some.
    if span_days < 365:
        reasons.append(f"only {span_days} days of attendance history (need 365)")

    return {
        "sufficient": not reasons,
        "employees": n_emp,
        "history_days": span_days,
        "reasons": reasons,
    }


def train_and_gate(db: Session) -> dict:
    """Train, compare against the baseline, and decide what serves.

    Never raises on a weak result — an inconclusive outcome is a legitimate
    answer and is recorded as such.
    """
    sufficiency = check_data_sufficiency(db)
    if not sufficiency["sufficient"]:
        decision = {
            "strategy": "baseline",
            "reason": "insufficient data to evaluate a model",
            "details": sufficiency["reasons"],
            "data": sufficiency,
        }
        _write_gate(decision)
        return decision

    from ai.risk_model import train_risk_model

    result = train_risk_model(db)
    if result.get("status") != "success":
        decision = {
            "strategy": "baseline",
            "reason": "training did not complete",
            "details": [str(result.get("message", result.get("status")))],
        }
        _write_gate(decision)
        return decision

    f1       = float(result.get("f1", 0.0))
    base_f1  = float(result.get("baseline_f1", 0.0))
    uplift   = round(f1 - base_f1, 2)

    promote = uplift >= MIN_UPLIFT_F1 and f1 >= MIN_F1

    if promote:
        reason = f"model beats the rule-based baseline by {uplift:.1f} F1 points"
        details = []
    else:
        reason = "baseline is as good as or better than the model"
        details = []
        if uplift < MIN_UPLIFT_F1:
            details.append(
                f"uplift {uplift:+.1f} F1 is below the {MIN_UPLIFT_F1} point "
                f"margin required to be distinguishable from noise"
            )
        if f1 < MIN_F1:
            details.append(f"model F1 {f1:.1f} is below the {MIN_F1} usability floor")

    decision = {
        "strategy": "model" if promote else "baseline",
        "reason": reason,
        "details": details,
        "model_f1": f1,
        "baseline_f1": base_f1,
        "uplift_f1": uplift,
        "data": sufficiency,
    }
    _write_gate(decision)
    return decision


def predict(db: Session, ref_date: date | None = None) -> list[dict]:
    """Risk scores from whichever predictor is currently trusted.

    Every row carries the strategy that produced it, so the interface can be
    honest with the user about where a number came from.
    """
    strategy = active_strategy()

    if strategy == "model":
        try:
            from ai.risk_model import predict_risk
            rows = predict_risk(db, ref_date)
            for r in rows:
                r["strategy"] = "model"
            return rows
        except Exception:
            # A missing or corrupt artifact must not take the feature down —
            # fall through to the rule.
            pass

    return _baseline_predict(db, ref_date)


def _baseline_predict(db: Session, ref_date: date | None = None) -> list[dict]:
    """The rule-based predictor.

    Reuses predire_sans_modele from the v1 module rather than reimplementing the
    rule: it already produces the field set the dashboard renders (nom, raisons,
    taux_absence, nb_absences, nb_retards) and it is the code path that has
    actually been exercised in the UI. Duplicating it here would mean two rules
    that could drift apart.
    """
    from ai.absenteeism_model import predire_sans_modele

    rows = predire_sans_modele(db) or []
    for r in rows:
        r["strategy"] = "baseline"
    return rows
