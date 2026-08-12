import os
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ============================================================================
# Database connection, driven entirely by environment variables so the same
# code runs locally, in Docker and in the cloud. The defaults preserve the
# original behaviour — SQL Server on localhost via Windows Authentication.
#
# Select the backend with DB_ENGINE:
#   DB_ENGINE=mssql     (default) -> Microsoft SQL Server via pyodbc
#   DB_ENGINE=postgres            -> PostgreSQL via psycopg (v3)
#
# Common vars: DB_SERVER, DB_PORT, DB_DATABASE, DB_USER, DB_PASSWORD
#
# SQL Server specifics:
#   DB_DRIVER  (default "ODBC Driver 17 for SQL Server")
#   With DB_USER + DB_PASSWORD -> SQL login auth.
#   Without them               -> Windows Authentication (trusted_connection).
# ============================================================================

DB_ENGINE = os.environ.get("DB_ENGINE", "mssql").lower()
DB_SERVER = os.environ.get("DB_SERVER", "localhost")
DB_PORT = os.environ.get("DB_PORT", "")
DB_DATABASE = os.environ.get("DB_DATABASE", "GestionRH_Intelligente")
DB_USER = os.environ.get("DB_USER", "")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")


def _build_mssql_url(database: str) -> str:
    driver = os.environ.get("DB_DRIVER", "ODBC Driver 17 for SQL Server").replace(" ", "+")
    if DB_USER and DB_PASSWORD:
        # SQL login authentication (works in Docker / cloud).
        host = f"{DB_SERVER},{DB_PORT}" if DB_PORT else DB_SERVER
        return (
            f"mssql+pyodbc://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}@{host}"
            f"/{database}?driver={driver}"
        )
    # Windows Authentication — the original local default.
    return f"mssql+pyodbc://{DB_SERVER}/{database}?driver={driver}&trusted_connection=yes"


def _build_postgres_url(database: str) -> str:
    port = DB_PORT or "5432"
    user = DB_USER or "postgres"
    return (
        f"postgresql+psycopg://{quote_plus(user)}:{quote_plus(DB_PASSWORD)}"
        f"@{DB_SERVER}:{port}/{database}"
    )


def build_url(database: str) -> str:
    if DB_ENGINE == "postgres":
        return _build_postgres_url(database)
    return _build_mssql_url(database)


CONNECTION_STRING = build_url(DB_DATABASE)

# Engine tuning:
#   pool_pre_ping     - drop connections whose link has gone stale
#   pool_recycle      - recycle every 30 min; SQL Server drops idle sessions
#   pool_size/overflow- 10 + 10 covers the dashboard fan-out plus a scheduler tick
#   fast_executemany  - pyodbc-only bulk insert speedup, applied on the mssql path
_engine_kwargs = dict(
    echo=False,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=10,
    max_overflow=10,
)
if DB_ENGINE != "postgres":
    _engine_kwargs["fast_executemany"] = True

Base = declarative_base()

# The engine is built on first use rather than at import.
#
# create_engine() eagerly imports the DBAPI driver, so building it at module
# level meant importing *any* model required pyodbc or psycopg to be installed
# — which made the business logic impossible to unit test, and broke tooling
# that only needs the schema. PEP 562 module __getattr__ keeps
# `from config.database import engine, SessionLocal` working unchanged while
# deferring the connection until something actually asks for it.
_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(CONNECTION_STRING, **_engine_kwargs)
    return _engine


def _get_sessionmaker():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())
    return _SessionLocal


def __getattr__(name):
    if name == "engine":
        return _get_engine()
    if name == "SessionLocal":
        return _get_sessionmaker()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ============================================================================
# Multi-tenancy — one database per client.
#
# Every route already depends on get_db(), so resolving the tenant here routes
# the whole application without touching a single endpoint. With no
# config/tenants.json present there is exactly one tenant and the behaviour is
# identical to before.
# ============================================================================
from config import tenants                          # noqa: E402

# fastapi is imported lazily inside get_db(): this module is also used by
# scripts, the ETL and the test suite, none of which should need the web
# framework installed just to open a database session.

# One engine (and connection pool) per tenant, built on first use and kept for
# the process lifetime. Creating an engine per request would exhaust the pool.
_engines: dict[str, object] = {}
_sessions: dict[str, object] = {}


def session_factory_for(tenant_key: str):
    """Session factory for one tenant, created on first use."""
    key = (tenant_key or tenants.DEFAULT_TENANT).strip().lower()
    if key in _sessions:
        return _sessions[key]

    database = tenants.database_for(key)
    if not database:
        raise KeyError(f"Unknown tenant {key!r}")

    if database == DB_DATABASE:
        # The default tenant reuses the module-level engine rather than opening
        # a second pool against the same database.
        # Note: PEP 562 module __getattr__ does not apply to name lookups from
        # inside the module itself, so call the accessors directly here.
        _sessions[key] = _get_sessionmaker()
        _engines[key] = _get_engine()
    else:
        eng = create_engine(build_url(database), **_engine_kwargs)
        _engines[key] = eng
        _sessions[key] = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    return _sessions[key]


def engine_for(tenant_key: str):
    session_factory_for(tenant_key)      # ensures the engine exists
    return _engines[(tenant_key or tenants.DEFAULT_TENANT).strip().lower()]


def get_db(request=None):
    """Yield a session bound to the requesting client's database.

    `request` is optional so that scripts, the scheduler and tests can still
    call get_db() directly — those fall back to the default tenant.
    """
    key = tenants.resolve_tenant(request)
    try:
        factory = session_factory_for(key)
    except KeyError:
        from fastapi import HTTPException
        # An unrecognised subdomain must not silently fall back to another
        # client's data — refuse the request instead.
        raise HTTPException(status_code=404, detail="Unknown workspace")

    db = factory()
    try:
        # Stash the tenant so downstream code (auth, audit) can see it.
        db.info["tenant"] = key
        yield db
    finally:
        db.close()
