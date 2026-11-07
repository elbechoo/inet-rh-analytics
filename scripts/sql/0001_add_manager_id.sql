-- Adds the reporting line to an existing Postgres deployment.
--
-- Why this file exists: the manager hierarchy was added to the ORM models after
-- this database was first created. SQLAlchemy's create_all() creates missing
-- tables but never alters existing ones, and there were no Alembic migrations
-- to carry the change, so the deployed schema silently drifted behind the
-- models. The drift was invisible to the application (which reads through the
-- ORM and tolerated the absent attribute) and surfaced only when dbt tested
-- Employe.manager_id against the real column list.
--
-- Idempotent: safe to run more than once.
--
--   Get-Content scripts\sql\0001_add_manager_id.sql | docker compose exec -T db psql -U inet -d inet_rh

BEGIN;

ALTER TABLE "Employe"
    ADD COLUMN IF NOT EXISTS manager_id INTEGER
    REFERENCES "Employe"(employe_id);

-- Backfill: the longest-serving employee in each department manages it.
-- Mirrors scripts/seed_demo.py so a migrated database and a freshly seeded one
-- end up with the same shape of hierarchy.
WITH mgr AS (
    SELECT departement_id,
           (array_agg(employe_id ORDER BY date_embauche, employe_id))[1] AS manager
    FROM "Employe"
    GROUP BY departement_id
)
UPDATE "Employe" e
   SET manager_id = m.manager
  FROM mgr m
 WHERE e.departement_id = m.departement_id
   AND e.employe_id <> m.manager
   AND e.manager_id IS NULL;

-- Department heads report to the longest-serving employee in the company.
-- That person is the root and keeps manager_id NULL, which is why the column is
-- nullable and why a not_null test on it would be wrong.
WITH racine AS (
    SELECT employe_id
      FROM "Employe"
     ORDER BY date_embauche, employe_id
     LIMIT 1
)
UPDATE "Employe" e
   SET manager_id = r.employe_id
  FROM racine r
 WHERE e.manager_id IS NULL
   AND e.employe_id <> r.employe_id;

COMMIT;

-- Expect exactly one employee with no manager.
SELECT count(*) FILTER (WHERE manager_id IS NULL) AS sans_manager,
       count(*) FILTER (WHERE manager_id IS NOT NULL) AS lignes_hierarchiques,
       count(DISTINCT manager_id) AS managers
  FROM "Employe";
