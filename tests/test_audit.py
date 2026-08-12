"""Audit trail.

The two properties that matter are structural, so they can be checked without a
database:

  * every action worth recording has a named constant, and
  * recording never raises — an audit failure must not roll back the business
    action it was recording.
"""
import pytest

from services import audit_service


def test_every_recorded_action_has_a_constant():
    """Action strings are constants, not literals scattered through routes, so
    a typo cannot silently create a second action name that filters miss."""
    expected = {
        "LEAVE_APPROVE", "LEAVE_REJECT", "LEAVE_CANCEL",
        "EMPLOYEE_CREATE", "EMPLOYEE_UPDATE", "EMPLOYEE_DELETE",
        "ROLE_CHANGE", "STATUS_CHANGE", "PASSWORD_RESET",
        "DOC_VALIDATE", "HOLIDAY_CHANGE", "DATA_IMPORT",
    }
    for name in expected:
        assert hasattr(audit_service, name), f"missing action constant {name}"
        assert isinstance(getattr(audit_service, name), str)


def test_action_names_are_unique():
    names = [
        audit_service.LEAVE_APPROVE, audit_service.LEAVE_REJECT,
        audit_service.LEAVE_CANCEL, audit_service.EMPLOYEE_CREATE,
        audit_service.EMPLOYEE_UPDATE, audit_service.EMPLOYEE_DELETE,
        audit_service.ROLE_CHANGE, audit_service.STATUS_CHANGE,
        audit_service.PASSWORD_RESET, audit_service.DOC_VALIDATE,
        audit_service.HOLIDAY_CHANGE, audit_service.DATA_IMPORT,
    ]
    assert len(names) == len(set(names))


def test_recording_never_raises(monkeypatch):
    """If the audit write fails, the leave approval it was recording must still
    succeed. A broken trail is an operational problem, not a user-facing error."""
    def explode(*a, **kw):
        raise RuntimeError("database is on fire")

    monkeypatch.setattr("config.database.session_factory_for", explode)

    # Must return normally despite the failure underneath.
    audit_service.record(
        action=audit_service.ROLE_CHANGE,
        actor={"user_id": 1, "role": "admin"},
        entite="Utilisateur", entite_id=42,
    )


def test_long_values_are_truncated_not_rejected():
    """Columns are bounded; an oversized comment must not blow up the write."""
    long_text = "x" * 5000
    out = audit_service._short(long_text)
    assert len(out) <= 500
    assert out.endswith("…")


def test_short_handles_none_and_dates():
    from datetime import date
    assert audit_service._short(None) is None
    assert audit_service._short(date(2026, 3, 20)) == "2026-03-20"
