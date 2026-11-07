import os
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config.database import get_db
from sqlalchemy.orm import Session
from models.models import Utilisateur

# Load .env into os.environ before anything reads it, so the API picks up its
# configuration whether it is started directly, by the scheduler, or in Docker.
load_dotenv()

# The signing secret is mandatory. Without it tokens would be signed with a
# predictable key and admin sessions could be forged, so refuse to boot instead.
# Generate one with:
#   python -c "import secrets; print(secrets.token_urlsafe(64))"
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == "inet-rh-secret-2025-change-in-production":
    raise RuntimeError(
        "SECRET_KEY is missing or still set to the insecure default. "
        "Set a strong random SECRET_KEY in your environment / .env file."
    )

ALGORITHM = "HS256"
COOKIE_NAME = "inet_token"
bearer = HTTPBearer(auto_error=False)


def _extract_token(request, credentials):
    # Prefer the httpOnly cookie; fall back to the Authorization header so
    # non-browser API clients (Power BI, scripts, integrations) still work.
    cookie_token = request.cookies.get(COOKIE_NAME)
    if cookie_token:
        return cookie_token
    if credentials:
        return credentials.credentials
    return None


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> dict:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = _extract_token(request, credentials)
    if not token:
        raise exc
    try:
        # PyJWT verifies both signature and expiry by default and raises
        # PyJWTError (including ExpiredSignatureError) on any problem.
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        if user_id is None:
            raise exc
    except jwt.PyJWTError:
        raise exc

    # The token must have been issued for the workspace being addressed.
    # Each client has its own database, so a token from Agency A replayed
    # against Agency B would otherwise resolve user_id to a different person
    # there. Tokens minted before this field existed carry no tenant and are
    # treated as belonging to the default workspace.
    from config.tenants import DEFAULT_TENANT, resolve_tenant
    token_tenant = payload.get("tenant") or DEFAULT_TENANT
    if token_tenant != resolve_tenant(request):
        raise exc

    user = db.query(Utilisateur).filter(Utilisateur.user_id == user_id).first()
    if not user:
        raise exc

    # Was this session ended before the token expired? Logout, a password reset
    # or an administrator killing a compromised session all set a revocation
    # point; anything issued before it is refused even though the signature and
    # expiry are still valid.
    try:
        from models.models import TokenRevoke
        rev = db.query(TokenRevoke).filter(TokenRevoke.user_id == user_id).first()
        if rev and rev.revoked_from:
            issued_at = payload.get("iat")
            if issued_at is not None:
                from datetime import datetime, timezone
                issued = datetime.fromtimestamp(int(issued_at), tz=timezone.utc)
                cutoff = rev.revoked_from
                if cutoff.tzinfo is None:
                    cutoff = cutoff.replace(tzinfo=timezone.utc)
                if issued < cutoff:
                    raise exc
    except HTTPException:
        raise
    except Exception:
        # The table may not exist yet on an older database. Failing open here is
        # the same security posture as before revocation existed, and is better
        # than locking every user out of a working system.
        pass

    return {
        "user_id": user.user_id,
        "role": user.role,
        "employe_id": user.employe_id,
        "tenant": token_tenant,
    }


def require_admin(current: dict = Depends(get_current_user)):
    if current["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current


def require_hr_or_admin(current: dict = Depends(get_current_user)):
    if current["role"] not in ("rh", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="HR or Admin access required")
    return current


def require_self_manager_or_hr(
    employe_id: int,
    current: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Own record, or a record belonging to someone who reports to you.

    Wider than require_self_or_hr by exactly one step: a manager can see their
    own team. Used for team views and approvals, never for payslips or
    documents - a manager having people report to them does not entitle them to
    read those.

    Only direct reports, not the whole subtree. Skip-level access is a policy
    decision a company should opt into, not something the code assumes.
    """
    if current["role"] in ("rh", "admin"):
        return current

    own = current.get("employe_id")
    if own == employe_id:
        return current

    from models.models import Employe
    target = db.query(Employe).filter(Employe.employe_id == employe_id).first()
    if target and target.manager_id == own:
        return current

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You may only access your own records or those of your team",
    )


def require_self_or_hr(employe_id: int, current: dict = Depends(get_current_user)):
    """Ownership guard for any route with an {employe_id} path parameter.

    Authentication alone is not enough: a logged-in employee could otherwise read
    a colleague's salary, leave history or attendance simply by changing the ID
    in the URL. HR and admins keep full access; everyone else is restricted to
    their own record.

    FastAPI resolves `employe_id` from the path, so this works as a plain
    route dependency:

        @router.get("/{employe_id}", dependencies=[Depends(require_self_or_hr)])
    """
    if current["role"] in ("rh", "admin"):
        return current
    if current.get("employe_id") != employe_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You may only access your own records",
        )
    return current
