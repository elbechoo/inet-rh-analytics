"""Tenant registry — one database per client.

Each agency gets its own database. Nothing is shared, so no query can leak
across clients even if a filter is forgotten: there is simply nothing to leak
into. That is the whole point of choosing this over a tenant_id column.

A tenant is resolved from the request in this order:
  1. the X-Tenant header      (API clients, scripts, Power BI)
  2. the Host subdomain       (agencya.inet-rh.tn -> "agencya")
  3. DEFAULT_TENANT           (single-client and local development)

Configure with a JSON file, path in TENANTS_FILE (default: config/tenants.json):

    {
      "agencya": {"database": "inet_agencya", "name": "Agency A"},
      "agencyb": {"database": "inet_agencyb", "name": "Agency B"}
    }

If the file is absent, the app runs exactly as before against DB_DATABASE —
so an existing single-client install is unaffected.
"""
import json
import os
import re
from functools import lru_cache

DEFAULT_TENANT = os.environ.get("DEFAULT_TENANT", "default")
TENANTS_FILE = os.environ.get("TENANTS_FILE", os.path.join("config", "tenants.json"))

# Hosts that never carry a tenant subdomain.
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal"}

# A tenant key becomes part of a database name, so keep it strict.
_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")


@lru_cache(maxsize=1)
def _registry() -> dict:
    """Load the tenant registry once. Restart the app to pick up changes."""
    tenants: dict = {}
    if os.path.exists(TENANTS_FILE):
        try:
            with open(TENANTS_FILE, encoding="utf-8") as f:
                raw = json.load(f)
            for key, cfg in raw.items():
                key = key.strip().lower()
                if not _KEY_RE.match(key):
                    raise ValueError(f"Invalid tenant key {key!r} in {TENANTS_FILE}")
                if not isinstance(cfg, dict) or not cfg.get("database"):
                    raise ValueError(f"Tenant {key!r} has no 'database' in {TENANTS_FILE}")
                tenants[key] = {"database": cfg["database"], "name": cfg.get("name", key)}
        except (json.JSONDecodeError, OSError) as e:
            raise RuntimeError(f"Could not read {TENANTS_FILE}: {e}") from e

    # The default tenant always exists and points at DB_DATABASE, so the app
    # still boots with no tenants.json at all.
    tenants.setdefault(DEFAULT_TENANT, {
        "database": os.environ.get("DB_DATABASE", "GestionRH_Intelligente"),
        "name": os.environ.get("TENANT_NAME", "iNET RH"),
    })
    return tenants


def is_multi_tenant() -> bool:
    """True once more than just the default tenant is configured."""
    return len(_registry()) > 1


def known_tenants() -> list[str]:
    return sorted(_registry().keys())


def tenant_config(key: str) -> dict | None:
    return _registry().get((key or "").strip().lower())


def database_for(key: str) -> str | None:
    cfg = tenant_config(key)
    return cfg["database"] if cfg else None


def _tenant_from_host(host: str) -> str | None:
    """Pull the leading label off the Host header, if it looks like a tenant."""
    if not host:
        return None
    host = host.split(":", 1)[0].strip().lower()   # drop the port
    if host in _LOCAL_HOSTS or not host:
        return None
    parts = host.split(".")
    if len(parts) < 3:            # inet-rh.tn -> no subdomain
        return None
    label = parts[0]
    if label in ("www", "api", "app"):
        return None
    return label


def resolve_tenant(request) -> str:
    """Work out which client this request belongs to.

    Falls back to the default tenant rather than raising, so a single-client
    install and local development behave exactly as before. An unknown
    subdomain on a multi-tenant deployment is rejected by the caller.
    """
    if request is None:
        return DEFAULT_TENANT

    # The Host header wins when it carries a subdomain: it is set by the
    # browser and pinned by TLS, whereas X-Tenant is chosen freely by the
    # caller. X-Tenant is only a fallback, for API clients hitting the apex
    # domain where there is no subdomain to read.
    from_host = _tenant_from_host(request.headers.get("host", ""))
    if from_host:
        return from_host

    header = request.headers.get("x-tenant")
    if header:
        return header.strip().lower()

    return DEFAULT_TENANT
