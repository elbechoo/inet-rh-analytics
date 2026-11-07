"""Shared rate limiter .

Uses slowapi (a Starlette/FastAPI wrapper around the `limits` library) to cap
how often sensitive endpoints - chiefly /auth/login - can be hit from one
client, blocking password brute-force attacks.

Install:  pip install slowapi

The default backend is in-memory, which is fine for a single process. When you
move to multiple workers / horizontal scaling, point `storage_uri` at Redis:
    Limiter(key_func=..., storage_uri="redis://localhost:6379")
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])
