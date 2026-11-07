"""Provision a new client workspace.

Creates the client's own database, builds the schema, seeds the holiday
calendar and creates their first administrator account.

    python scripts/provision_tenant.py --key agencya --name "Agency A"
    python scripts/provision_tenant.py --key agencya --name "Agency A" --admin admin@agencya.tn

The tenant is appended to config/tenants.json. Restart the API afterwards -
the registry is read once at startup.

Nothing is shared between clients: separate database, separate schema, separate
users. A query cannot leak across workspaces because there is nothing to leak
into.
"""
import argparse
import json
import os
import re
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

from config import tenants
from config.database import DB_ENGINE, DB_DATABASE, build_url, _engine_kwargs

KEY_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")


def _server_url() -> str:
    """A connection to the server itself, for CREATE DATABASE."""
    # master on SQL Server, postgres on PostgreSQL - you cannot create a
    # database from inside the one you are creating.
    return build_url("postgres" if DB_ENGINE == "postgres" else "master")


def create_database(db_name: str) -> bool:
    """Create the database if it does not exist. Returns True if created."""
    eng = create_engine(_server_url(), isolation_level="AUTOCOMMIT")
    try:
        with eng.connect() as conn:
            if DB_ENGINE == "postgres":
                exists = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": db_name}
                ).scalar()
                if exists:
                    return False
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
            else:
                exists = conn.execute(
                    text("SELECT 1 FROM sys.databases WHERE name = :n"), {"n": db_name}
                ).scalar()
                if exists:
                    return False
                conn.execute(text(f"CREATE DATABASE [{db_name}]"))
        return True
    finally:
        eng.dispose()


def register(key: str, db_name: str, display: str) -> None:
    path = tenants.TENANTS_FILE
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    data = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    data[key] = {"database": db_name, "name": display}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main() -> None:
    ap = argparse.ArgumentParser(description="Provision a new client workspace")
    ap.add_argument("--key", required=True, help="subdomain, e.g. agencya")
    ap.add_argument("--name", help="display name (defaults to the key)")
    ap.add_argument("--database", help="database name (default: inet_<key>)")
    ap.add_argument("--admin", help="email/username for the first admin account")
    ap.add_argument("--no-holidays", action="store_true", help="skip the holiday calendar")
    args = ap.parse_args()

    key = args.key.strip().lower()
    if not KEY_RE.match(key):
        sys.exit(f"Invalid key {key!r}: use lowercase letters, digits, '-' and '_'.")
    if key == tenants.DEFAULT_TENANT:
        sys.exit(f"{key!r} is the default workspace and already exists.")

    db_name = args.database or f"inet_{key}"
    display = args.name or key

    if db_name == DB_DATABASE:
        sys.exit(f"Refusing to use {db_name!r} - that is the default workspace's database.")

    print(f"Provisioning '{display}'  (key={key}, database={db_name})\n")

    created = create_database(db_name)
    print(f"  database   {'created' if created else 'already existed'}")

    # Build the schema in the new database. Importing models registers every
    # table on Base.metadata.
    import models.models  # noqa: F401
    from config.database import Base

    eng = create_engine(build_url(db_name), **_engine_kwargs)
    try:
        Base.metadata.create_all(bind=eng)
        print(f"  schema     {len(Base.metadata.tables)} tables")

        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=eng)
        db = Session()
        try:
            if not args.no_holidays:
                from datetime import date
                from services.holiday_service import seed
                y = date.today().year
                res = seed(db, y, y + 2)
                print(f"  holidays   {res['created']} days ({y}-{y + 2})")

            if args.admin:
                print(f"\n  Admin account for {args.admin} is NOT created by this script.")
                print("  Create it from the app, or with your existing user-creation flow,")
                print("  so the password is set interactively and never passes through a")
                print("  command line or shell history.")
        finally:
            db.close()
    finally:
        eng.dispose()

    register(key, db_name, display)
    print(f"\n  registered in {tenants.TENANTS_FILE}")
    print(f"\nDone. Point {key}.yourdomain.tn at the app and restart the API.")
    print("The registry is loaded once at startup, so the restart is required.")


if __name__ == "__main__":
    main()
