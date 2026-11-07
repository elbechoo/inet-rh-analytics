# iNET RH - dbt analytics layer

Transforms the operational HR database into a Kimball star schema that Power BI
connects to. SQL only, version-controlled, tested on every run.

```
sources (hr_app)      the application's Postgres tables, read-only
    ↓
staging/              one model per source table - rename, cast, no logic
    ↓
intermediate/         int_calendrier - the single definition of a working day
    ↓
marts/                dim_date · dim_employe · dim_departement
                      fct_pointage · fct_absence · fct_conge
```

## Why the calendar sits in its own model

`int_calendrier` answers one question - *is this a working day* - and every
fact table joins to it rather than deciding for itself.

That is not an abstraction for its own sake. In the application the rule was
written separately at each call site, and the versions drifted: they excluded
weekends but not public holidays. Leave spanning Aïd was charged to the
employee's own balance, and nobody who stayed home on a public holiday was
recorded as absent - which then fed the absenteeism model as real signal.
Defining it once makes that class of drift impossible.

## Tests

Beyond the usual `unique` / `not_null` / `relationships`:

| Test | Catches |
|---|---|
| `assert_no_absence_on_jour_ferie` | The original bug - absences recorded on public holidays |
| `assert_no_pointage_on_weekend` | Badly parsed dates or a misconfigured terminal |
| `assert_conge_dates_coherentes` | Leave ending before it starts |
| `assert_jours_consommes_positifs` | Approved leave covering no working day at all |

`fct_conge` recomputes the days charged instead of trusting the source column,
and exposes `ecart_jours` - the gap between what the application charged and
what it should have. Across the demo dataset that gap is 440 days.

## Running it

dbt runs in a container. That is not ceremony: dbt supports Python 3.9-3.12 and
several of its dependencies have no wheels beyond that, so pinning the
interpreter in an image avoids fighting whatever Python the host happens to
have.

```bash
# from the repository root, with Docker Desktop running
docker compose up -d db

docker compose --profile analytics run --rm dbt deps     # once
docker compose --profile analytics run --rm dbt build    # run + test
```

`dbt build` rather than `dbt run`: it tests each model as it is built, so a
failure stops the chain instead of propagating into the marts.

The project directory is mounted into the container, so edits to a model take
effect on the next run with no rebuild.

### Documentation and lineage

```bash
docker compose --profile analytics run --rm dbt docs generate
docker compose --profile analytics run --rm --service-ports dbt docs serve --port 8080
```

### Running it without Docker

Only if the host has Python 3.12 or older:

```bash
pip install dbt-postgres
dbt deps
export DB_PASSWORD=...
dbt build --profiles-dir .
```

## Connecting Power BI

Point it at the `analytics_marts` schema and import the three dimensions and
three fact tables. The relationships follow the keys: `date_id`,
`employe_id`, `departement_id`.

`dim_date.est_jour_ouvrable` is the denominator for attendance rates - use it
rather than counting calendar days in DAX, so the report and the warehouse
agree on what a working day is.
