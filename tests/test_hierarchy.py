"""Reporting hierarchy and session revocation."""
import pytest
from fastapi.routing import APIRoute


@pytest.fixture(scope="module")
def app():
    from api.main import app as fastapi_app
    return fastapi_app


def _routes(app):
    return [r for r in app.routes if isinstance(r, APIRoute)]


def _deps(route) -> set[str]:
    return {
        d.call.__name__
        for d in route.dependant.dependencies
        if getattr(d, "call", None) is not None and hasattr(d.call, "__name__")
    }


def test_employee_model_has_a_reporting_line():
    # backref attributes are created when the mappers are configured, which
    # SQLAlchemy defers until first use - force it before asserting.
    from sqlalchemy.orm import configure_mappers
    from models.models import Employe
    configure_mappers()

    assert hasattr(Employe, "manager_id")
    assert hasattr(Employe, "manager")
    assert hasattr(Employe, "subordonnes")


def test_manager_id_is_nullable():
    """The top of the hierarchy reports to nobody, and a new hire may not have a
    manager assigned yet - a non-nullable column would make both impossible."""
    from models.models import Employe
    assert Employe.__table__.c.manager_id.nullable is True


def test_team_view_allows_managers_but_not_peers(app):
    """/equipe uses the wider guard; everything else stays own-record-or-HR.

    The distinction matters: managing someone justifies seeing who they are, not
    reading their documents or risk score."""
    team = [r for r in _routes(app) if r.path.endswith("/{employe_id}/equipe")]
    assert team, "team endpoint missing"
    assert "require_self_manager_or_hr" in _deps(team[0])

    # The plain record endpoint must NOT have been widened by accident.
    plain = [r for r in _routes(app)
             if r.path == "/employes/{employe_id}" and "GET" in r.methods]
    assert plain
    assert "require_self_or_hr" in _deps(plain[0])


def test_employee_listing_is_paginated(app):
    """Unbounded listing is a scalability bug: the top bar fetches this on every
    page load."""
    listing = [r for r in _routes(app)
               if r.path == "/employes/" and "GET" in r.methods]
    assert listing
    params = {p.name for p in listing[0].dependant.query_params}
    assert {"limit", "offset"} <= params, f"no pagination params, got {params}"


def test_listing_limit_is_capped(app):
    """A caller must not be able to ask for the entire table.

    Reads the constraint from the field metadata: FastAPI stores Query bounds as
    annotated-types objects rather than plain attributes, so `.le` is not
    directly available."""
    listing = [r for r in _routes(app)
               if r.path == "/employes/" and "GET" in r.methods][0]
    limit = next(p for p in listing.dependant.query_params if p.name == "limit")

    upper = None
    for constraint in getattr(limit.field_info, "metadata", []):
        if hasattr(constraint, "le"):
            upper = constraint.le
        elif hasattr(constraint, "lt"):
            upper = constraint.lt - 1

    assert upper is not None, "limit has no upper bound - a caller could request everything"
    assert upper <= 1000


# ── Session revocation ──────────────────────────────────────

def test_revocation_table_exists():
    from models.models import TokenRevoke
    assert TokenRevoke.__tablename__ == "TokenRevoke"
    assert "revoked_from" in TokenRevoke.__table__.c


def test_tokens_carry_an_issued_at_claim():
    """Revocation compares the token's issue time against a cutoff. Without iat
    there is nothing to compare and logout could not invalidate anything."""
    import inspect
    from api.routes import auth
    src = inspect.getsource(auth.create_access_token)
    assert '"iat"' in src, "token has no iat claim - revocation cannot work"


def test_logout_records_a_revocation_point():
    import inspect
    from api.routes import auth
    src = inspect.getsource(auth.logout)
    assert "TokenRevoke" in src
    assert "delete_cookie" in src


def test_password_reset_revokes_sessions():
    """A reset is usually a response to compromise; leaving the attacker's token
    alive would defeat it."""
    import inspect
    from api.routes import admin
    src = inspect.getsource(admin.reset_password)
    assert "TokenRevoke" in src, "password reset does not end existing sessions"
