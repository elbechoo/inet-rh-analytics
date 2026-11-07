<div align="center">

# iNET RH - Smart HR Management

**Attendance, leave and absenteeism analytics for Tunisian companies**

*Built at iNET · 2025-2026*

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?style=flat-square&logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-F7931E?style=flat-square&logo=scikitlearn&logoColor=white)](https://scikit-learn.org)

</div>

---

## What it does

HR departments collect a lot of data - clock-ins, leave, absences, training, missions - and rarely use it for anything beyond payroll. iNET RH turns that data into something a manager will actually read, and flags employees whose attendance is deteriorating before it becomes a resignation.

Three separate workspaces, each with its own permissions:

| Workspace | Who | What they can do |
|---|---|---|
| **Employee** | Any staff member | Clock in/out, request leave, view their own history and documents |
| **HR** | HR managers | Company-wide dashboards, approve leave, absence tracking, risk alerts |
| **Admin** | System administrators | Users, departments, configuration, audit logs |

---

## Screenshots

<!-- Add your own: capture the HR dashboard, the employee space and the holiday page. -->

| HR dashboard | Employee space |
|---|---|
| _(screenshot)_ | _(screenshot)_ |

---

## Run it

The whole stack runs in containers - database, API, frontend and a reverse proxy with automatic HTTPS.

```bash
git clone https://github.com/<you>/inet-rh.git
cd inet-rh
cp .env.example .env          # set SECRET_KEY and DB_PASSWORD
docker compose up --build -d
```

Seed a demo company with a year of generated history:

```bash
docker compose exec api python scripts/seed_demo.py       # departments, employees, accounts
docker compose exec api python scripts/seed_holidays.py   # Tunisian public holidays
docker compose exec api python scripts/seed_history.py --days 365
docker compose exec api python scripts/seed_extras.py     # training, missions, documents
```

Then open **https://localhost**. The seeder prints the login for the admin and HR accounts.

For a real domain, set `SITE_ADDRESS=hr.yourcompany.tn` in `.env` - Caddy fetches a Let's Encrypt certificate on its own.

---

## Architecture

```
                    ┌─────────────────┐
                    │  Caddy (proxy)  │  automatic HTTPS
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    Next.js 16   │  three role-based workspaces
                    │   React 19 · TS │  /api/* proxied server-side
                    └────────┬────────┘
                             │  httpOnly cookie, same-origin
                    ┌────────▼────────┐
                    │    FastAPI      │  auth · ownership checks · rate limiting
                    │  routes         │
                    │  services       │  business rules
                    │  repositories   │  data access
                    │  ai/            │  absenteeism model
                    └────────┬────────┘
                             │  SQLAlchemy 2.0
                    ┌────────▼────────┐
                    │   PostgreSQL    │  (SQL Server also supported)
                    └─────────────────┘
```

Layered on purpose: routes handle HTTP and permissions, services hold the business rules, repositories own the SQL. The AI module reads through the same repositories, so it can never disagree with what the dashboard shows.

---

## Security

Most of the engineering here went into access control rather than features.

- **Authentication is enforced at the router level**, not per endpoint - a new route cannot be added without it
- **JWT in an httpOnly cookie**, so a cross-site scripting bug cannot steal a session
- **Ownership checks on every route that takes an ID** - an employee cannot read a colleague's payslip, leave history or risk score by changing the URL
- **Role separation** - HR analytics and model internals are unreachable from an employee account
- **Rate limiting on login** (5 attempts per IP per 15 minutes)
- **Security headers** - `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, HSTS over TLS
- **bcrypt** password hashing, and no secret has a default value: the app refuses to boot without `SECRET_KEY`
- **Document downloads return 404, not 403**, for files you do not own - a 403 would confirm the file exists and let IDs be enumerated

Multi-tenancy is available for hosting several companies from one deployment: each gets a **separate database**, selected by subdomain, and tokens are bound to the workspace that issued them.

---

## Public holidays

Leave and absence calculations are holiday-aware, which most generic HR software imported into Tunisia gets wrong.

Without it, an employee taking leave across Aïd is charged those days from their own balance, and nobody clocking in on a public holiday is recorded as absent - which then feeds the absenteeism model as real signal. The calendar covers the fixed civil holidays plus Aïd El-Fitr, Aïd El-Idha, Ras El Am Hejri and Mouled.

Islamic dates move each year and are fixed by moon sighting, so they are stored per year and HR can correct them from the interface when the official announcement differs.

---

## The AI module

Predicts which employees are at risk of increasing absenteeism, and explains why.

**How it works.** Features are built from attendance history - absence rate, lateness frequency, how absences cluster around weekends, deviation from the employee's own department. A random forest produces a probability; the explanation layer compares each feature against the department median and reports the ones that actually drive the score.

**Benchmarked on real data.** Results below are from the UCI *Absenteeism at
Work* dataset - a Brazilian courier company, 740 absence records across 36
employees - not from generated data. The task: given what is known when someone
calls in, will this absence cost a full working day or more?

| Method | F1 | Precision | Recall | AUC |
|---|---|---|---|---|
| Majority class | 0.0 | 0.0 | 0.0 | 50.0 |
| Rule (medical reason code) | 55.5 | 68.9 | 48.2 | 67.7 |
| Logistic regression | 59.3 | 68.1 | 55.0 | 78.5 |
| **Random forest** | **70.8** | 69.0 | 74.9 | 80.2 |
| Gradient boosting | 69.2 | 68.1 | 71.8 | 82.8 |

**+15.3 F1 points over the best hand-written rule.**

**Why the split is grouped by employee.** Absences are very unevenly
distributed - one employee accounts for 113 of the 740 rows. Split at random
and the same person appears in training and test, so the model learns *that
individual's* habits and scores well by recognising them. Splitting by employee
means every person in the test set is unseen, which is the situation the model
faces in production.

The difference is measurable: the same random forest scores **77.0** on a random
split and **70.8** grouped. Those 6 points are memorisation, not skill. Both
numbers are printed by `python -m ai.benchmark_uci` so the gap is visible rather
than hidden.

**The model does not get to assume it is useful.** Every deployment trains on
its own data, scores against the rule-based baseline on a held-out temporal
split, and the model is only promoted to serving if it wins by at least 5 F1
points. Otherwise the rule serves and the system says so - `GET /ai/strategy`
reports which is active and why. On data where behaviour is stable, the rule is
the correct answer, and pretending otherwise would be dishonest.

**The bundled demo data is generated**, so figures produced from it are
illustrative only. The benchmark above is the one to judge the model on.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Recharts |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2 |
| Database | PostgreSQL 16 (SQL Server 2022 also supported) |
| Auth | PyJWT, bcrypt, httpOnly cookies, slowapi |
| ML | scikit-learn, pandas, numpy |
| Infrastructure | Docker Compose, Caddy, Alembic |
| Reporting | Power BI (star schema and DAX measures included) |

---

## Project structure

```
api/            FastAPI routes, dependencies, auth
services/       business rules (leave, attendance, holidays)
repositories/   data access
models/         SQLAlchemy models
ai/             feature engineering, model, explanations
config/         database connection, tenant registry
demo/           attendance simulator
scripts/        seeding, imports, data audits
notifications/  email digests, scheduler
etl/            star schema loader
powerbi/        theme, DAX measures, star schema SQL
frontend-next/  Next.js application
migrations/     Alembic
```

---

## Development without Docker

```bash
python -m venv venv && venv\Scripts\activate     # Windows
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000

cd frontend-next && npm install && npm run dev
```

The database connection is entirely environment-driven (`DB_ENGINE=mssql|postgres`), so switching backends needs no code change. Copy `.env.example` to `.env` and fill it in.

---

## Data tooling

| Script | Purpose |
|---|---|
| `seed_demo.py` | Fictional company - departments, employees, accounts |
| `seed_history.py` | Backfills realistic attendance over any period |
| `seed_holidays.py` | Tunisian public holiday calendar |
| `audit_holiday_absences.py` | Finds absences wrongly recorded on holidays |
| `audit_holiday_conges.py` | Finds leave over-charged because it spanned a holiday |
| `import_absenteeism_dataset.py` | Imports the UCI Absenteeism at Work dataset |
| `provision_tenant.py` | Creates a new isolated client workspace |

The two audit scripts are read-only by default and report before they change anything.

---

## Project info

**Author** - Hechem Zenati
**Context** - built at iNET, 2025-2026
**Status** - functional; demo data is simulated
