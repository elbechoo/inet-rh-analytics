"""Access control.

Pins the two holes found during the security pass:

  * an authenticated employee could read a colleague's records by changing the
    ID in the URL (IDOR), and
  * POST /employes/ created a user account with a caller-supplied role, so any
    employee could mint themselves an administrator login.

These assert the route table itself rather than making HTTP calls: the point is
that no endpoint is left unguarded, and that is a property of the wiring. A
route added later without a guard fails here.
"""
import pytest
from fastapi.routing import APIRoute


@pytest.fixture(scope="module")
def app():
    from api.main import app as fastapi_app
    return fastapi_app


def _routes(app):
    return [r for r in app.routes if isinstance(r, APIRoute)]


def _dependency_names(route) -> set[str]:
    names = set()
    for dep in route.dependant.dependencies:
        call = getattr(dep, "call", None)
        if call is not None and hasattr(call, "__name__"):
            names.add(call.__name__)
    return names


# Login must be reachable without a token, and these carry no data.
PUBLIC_PATHS = {"/", "/health", "/auth/login", "/auth/logout",
                "/docs", "/openapi.json", "/redoc"}


def test_every_endpoint_requires_authentication(app):
    """Authentication is enforced on every route so that adding one cannot
    accidentally publish it.

    Covers /admin too. Those routes declare their guard as a function parameter
    (`_: dict = Depends(require_admin)`) rather than in the decorator, which is
    easy to miss when skimming — and /admin/users/{id}/role can change anyone's
    role, so an unguarded one there would be the worst hole in the system.
    Inspecting the resolved dependency tree catches both styles.
    """
    unguarded = []
    for route in _routes(app):
        if route.path in PUBLIC_PATHS:
            continue
        deps = _dependency_names(route)
        if not deps & {"get_current_user", "require_hr_or_admin",
                       "require_admin", "require_self_or_hr"}:
            unguarded.append(f"{list(route.methods)} {route.path}")
    assert not unguarded, "endpoints with no authentication: " + ", ".join(unguarded)


def test_routes_with_an_employee_id_check_ownership(app):
    """Any route taking {employe_id} must verify the caller owns that record,
    or be restricted to HR."""
    missing = []
    for route in _routes(app):
        if "{employe_id}" not in route.path:
            continue
        deps = _dependency_names(route)
        if not deps & {"require_self_or_hr", "require_hr_or_admin", "require_admin"}:
            missing.append(f"{list(route.methods)} {route.path}")
    assert not missing, "no ownership check on: " + ", ".join(missing)


def test_creating_an_employee_is_restricted(app):
    """POST /employes/ also creates a Utilisateur with a role. Unrestricted,
    that is privilege escalation from any staff account."""
    for route in _routes(app):
        if route.path == "/employes/" and "POST" in route.methods:
            deps = _dependency_names(route)
            assert deps & {"require_hr_or_admin", "require_admin"}, \
                "POST /employes/ must be HR/admin only — it can create an admin account"
            return
    pytest.fail("POST /employes/ not found")


def test_ai_analytics_are_hr_only(app):
    """Risk scores and model internals are confidential. The personal alerts
    feed is the deliberate exception and filters to the caller's own record."""
    employee_reachable = {"/ai/alertes", "/ai/alertes/{alerte_id}/lue"}
    leaked = []
    for route in _routes(app):
        if not route.path.startswith("/ai/"):
            continue
        if route.path in employee_reachable:
            continue
        if not _dependency_names(route) & {"require_hr_or_admin", "require_admin"}:
            leaked.append(f"{list(route.methods)} {route.path}")
    assert not leaked, "AI endpoints reachable by employees: " + ", ".join(leaked)


def test_duplicate_login_endpoint_is_gone(app):
    """/employes/login duplicated /auth/login without the rate limit, which made
    it a credential oracle for any authenticated user."""
    paths = {r.path for r in _routes(app)}
    assert "/employes/login" not in paths
