"""
api/utils/cache.py — minimal in-process TTL cache for read-heavy endpoints.

The dashboards aggregate ~200 k pointage rows on every render. The underlying
data only changes when the simulation or the ETL runs (twice a day plus an
overnight refresh), so memoising the answer for 2 minutes is safe and removes
the cold-query lag the jury will see during the demo.

Use it as a decorator on a route handler:

    @router.get("/kpis/global")
    @ttl_cache(seconds=120, key="kpis_global")
    def kpis_global(db: Session = Depends(get_db)):
        ...

The decorator stores results in a process-local dict, keyed by an explicit key
plus all positional / keyword arguments *excluding* the `db` Session (sessions
are not hashable and would otherwise force a miss every call).

Manual invalidation (call after a write that changes aggregates):

    invalidate("kpis_global", "kpis_departement", "stats_evolution")

A safety net: any entry older than 10 minutes is dropped automatically so the
cache can never grow without bound.
"""
from __future__ import annotations

import time
from functools import wraps
from threading import RLock
from typing import Any, Callable

_LOCK: RLock = RLock()
_STORE: dict[str, tuple[float, Any]] = {}
_HARD_TTL = 600  # absolute upper bound, regardless of decorator setting


def _make_key(prefix: str, args: tuple, kwargs: dict) -> str:
    # Drop unhashable bits (SQLAlchemy Session) and rely on the prefix + scalars.
    safe_args = tuple(a for a in args if isinstance(a, (str, int, float, bool, tuple)))
    safe_kw = tuple(sorted((k, v) for k, v in kwargs.items()
                           if isinstance(v, (str, int, float, bool, tuple))))
    return f"{prefix}::{safe_args}::{safe_kw}"


def ttl_cache(seconds: int, key: str) -> Callable:
    """Decorator: memoise the function for `seconds` seconds under `key`."""
    ttl = min(seconds, _HARD_TTL)

    def deco(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            k = _make_key(key, args, kwargs)
            now = time.monotonic()
            with _LOCK:
                hit = _STORE.get(k)
                if hit is not None and (now - hit[0]) < ttl:
                    return hit[1]
            value = fn(*args, **kwargs)
            with _LOCK:
                _STORE[k] = (now, value)
            return value
        return wrapper
    return deco


def invalidate(*keys: str) -> None:
    """Drop every cache entry whose key starts with one of the given prefixes."""
    if not keys:
        return
    with _LOCK:
        for k in list(_STORE.keys()):
            if any(k.startswith(prefix + "::") for prefix in keys):
                _STORE.pop(k, None)


def clear_all() -> None:
    with _LOCK:
        _STORE.clear()
