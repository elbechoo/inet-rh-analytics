import os
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from config.database import get_db
from services import employe_service
from pydantic import BaseModel, Field
from datetime import datetime, timedelta, timezone
from api.deps import SECRET_KEY, ALGORITHM, COOKIE_NAME
from api.limiter import limiter

router = APIRouter()

ACCESS_TOKEN_EXPIRE_HOURS = 8

# Auth cookie flags.
#  - httponly=True   -> JavaScript cannot read it, so an XSS can't steal the token.
#  - samesite="lax"  -> not sent on cross-site requests (CSRF hardening); fine
#                       because the frontend talks to the API same-origin via the
#                       Next.js /api proxy.
#  - secure           -> only sent over HTTPS. MUST be True in production. Driven by
#                       env so local http dev still works: set COOKIE_SECURE=true
#                       once you're behind HTTPS.
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
COOKIE_MAX_AGE = ACCESS_TOKEN_EXPIRE_HOURS * 3600


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=200)


def create_access_token(user_id: int, role: str, tenant: str) -> str:
    # The tenant is signed into the token. Each client has its own database, so
    # without this a token issued by Agency A would be accepted on Agency B's
    # subdomain and resolve to whichever user happens to hold the same id there
    # — possibly an administrator.
    payload = {
        "sub": str(user_id),
        "role": role,
        "tenant": tenant,
        "exp": datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


@router.post("/login")
@limiter.limit("5/15minutes")  # brute-force guard: 5 tries per IP per 15 min
def login(request: Request, data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    result = employe_service.authenticate_user(db, data.username, data.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Bind the token to the workspace it was issued for.
    from config.tenants import resolve_tenant
    token = create_access_token(result["user_id"], result["role"], resolve_tenant(request))
    _set_auth_cookie(response, token)
    # Token is still returned in the body for non-browser API clients. Browsers
    # rely on the httpOnly cookie and should NOT persist this value.
    return {**result, "access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout(response: Response):
    """Clear the auth cookie server-side so the session truly ends."""
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"message": "Logged out"}
