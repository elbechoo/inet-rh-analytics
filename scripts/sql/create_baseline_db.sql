-- Creates a throwaway empty database for `alembic revision --autogenerate`.
--
-- Autogenerate works by diffing the ORM models against a live database, so it
-- has to run against an EMPTY one to emit the full schema as a baseline. Run
-- against a populated database it would emit only the difference, which is not
-- a baseline and would leave a fresh deployment with no tables.
--
-- Dropped again once the baseline revision exists - see scripts/sql/drop_baseline_db.sql.
--
--   docker compose cp scripts\sql\create_baseline_db.sql db:/tmp/c.sql
--   docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d postgres -f /tmp/c.sql'

CREATE DATABASE inet_rh_baseline;
