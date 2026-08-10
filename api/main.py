import os
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from config.database import engine, Base
from api.limiter import limiter
from api.deps import get_current_user, require_hr_or_admin
from api.routes import employe, pointage, conge, ai, document, mission, formation, auth, admin, import_data, holiday

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title       = "INET RH Intelligente",
    description = "API pour la gestion RH intelligente",
    version     = "1.0.0"
)

# Rate limiter + its 429 handler.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Force HTTPS in production. Off by default so local http dev is unaffected;
# set FORCE_HTTPS=true once TLS is terminated (reverse proxy / load balancer).
if os.environ.get("FORCE_HTTPS", "false").lower() == "true":
    app.add_middleware(HTTPSRedirectMiddleware)


# Security response headers on every request.
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    # Enable HSTS only when served over HTTPS (avoids breaking local http dev).
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials = True,
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers     = ["Authorization", "Content-Type"],
)

# Authentication is enforced at the router level so no endpoint can be added
# later without it. Only /auth is public (login must be reachable anonymously).
AUTHED = [Depends(get_current_user)]
HR_ONLY = [Depends(require_hr_or_admin)]

app.include_router(auth.router, prefix="/auth", tags=["Auth"])

app.include_router(employe.router,   prefix="/employes",   tags=["Employes"],   dependencies=AUTHED)
app.include_router(pointage.router,  prefix="/pointages",  tags=["Pointage"],   dependencies=AUTHED)
app.include_router(conge.router,     prefix="/conges",     tags=["Conges"],     dependencies=AUTHED)
app.include_router(document.router,  prefix="/documents",  tags=["Documents"],  dependencies=AUTHED)
app.include_router(mission.router,   prefix="/missions",   tags=["Missions"],   dependencies=AUTHED)
app.include_router(formation.router, prefix="/formations", tags=["Formations"], dependencies=AUTHED)

# Absenteeism risk scores and model internals are confidential HR data, but an
# employee still needs their own alerts for the notification bell. The guard is
# therefore per-route inside ai.py (HR_ONLY on everything except the personal
# alerts feed, which filters to the caller's own record) rather than blanket
# here — a blanket HR_ONLY silently emptied every employee's notifications.
app.include_router(ai.router, prefix="/ai", tags=["IA"], dependencies=AUTHED)

# Bring-your-own-data import. HR/admin only — it writes employees and history.
app.include_router(import_data.router, prefix="/import", tags=["Import"], dependencies=HR_ONLY)

# Public-holiday calendar. Read is fine for any authenticated user (employees
# need to see it when planning leave), but writing changes how every leave
# request is counted, so edits are HR/admin only — enforced per-route below.
app.include_router(holiday.router, prefix="/holidays", tags=["Jours fériés"], dependencies=AUTHED)

app.include_router(admin.router, prefix="/admin", tags=["Admin"])


@app.get("/")
def root():
    return {"message": "INET RH API is running!"}


@app.get("/health")
def health():
    return {"status": "ok"}


# Warm-up: the three heavy dashboard endpoints are 2-4 s on a cold cache; we run
# them once at startup in a background thread so the first HR Manager to open the
# page in the morning hits a warm cache, not a cold scan.
@app.on_event("startup")
def warm_dashboard_cache():
    import threading
    from concurrent.futures import ThreadPoolExecutor

    def _open_one():
        from config.database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1")).scalar()
        finally:
            db.close()

    def _warm():
        from config.database import engine, SessionLocal
        from api.routes.pointage import (
            kpis_global, kpis_par_departement, evolution_annuelle,
        )

        pool_size = (engine.pool.size() or 5) + (engine.pool.overflow() or 0)
        n = max(pool_size, 10)
        try:
            with ThreadPoolExecutor(max_workers=n) as ex:
                list(ex.map(lambda _: _open_one(), range(n)))
        except Exception:
            pass

        db = SessionLocal()
        try:
            kpis_global(db)
            kpis_par_departement(db)
            evolution_annuelle(db)
        except Exception:
            pass
        finally:
            db.close()

    threading.Thread(target=_warm, daemon=True, name="cache-warmup").start()
