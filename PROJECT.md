# iNET RH - Intelligent HR Management System
> Final Year Project (PFE) - Complete Technical Documentation

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Database Schema](#4-database-schema)
5. [Backend - API Routes](#5-backend--api-routes)
6. [Frontend - Pages](#6-frontend--pages)
7. [Authentication & Security](#7-authentication--security)
8. [AI Model](#8-ai-model)
9. [ETL Pipeline](#9-etl-pipeline)
10. [Simulation System](#10-simulation-system)
11. [Scheduler Jobs](#11-scheduler-jobs)
12. [Power BI Dashboards](#12-power-bi-dashboards)
13. [Testing & Quality](#13-testing--quality)
14. [Project Structure](#14-project-structure)
15. [How to Run](#15-how-to-run)

---

## 1. Project Overview

**iNET RH** is a full-stack intelligent HR management platform built as a PFE (final year project). It manages the complete employee lifecycle - from daily attendance tracking to AI-powered absenteeism risk prediction - and exposes everything through a modern web interface and Power BI dashboards.

### Key Capabilities
- Role-based access: **Admin**, **HR Manager**, **Employee**
- Real-time attendance tracking (pointage) with anomaly detection
- Leave (congé) and absence management with approval workflows
- Training (formation) and mission tracking
- Document request and PDF generation
- AI model predicting which employees are at absenteeism risk, validated by temporal split, 5-fold cross-validation, and a rule-based baseline
- Isolation Forest anomaly detection on attendance behaviour
- Automated daily simulation of realistic employee behavior
- ETL pipeline feeding (a) flat KPI tables and (b) a Kimball star-schema data warehouse
- APScheduler automating all jobs (simulation, ETL, email, AI retraining)
- Power BI dashboards connected to live SQL Server views
- 17 unit tests covering core business logic (no database required)
- 10 years of historical data (2016-2026) seeded with seasonal patterns

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│                                                                 │
│   ┌─────────────────────────┐    ┌──────────────────────────┐  │
│   │   Next.js 16 Frontend   │    │    Power BI Desktop       │  │
│   │   (React 19, TypeScript)│    │   (connected via ODBC)    │  │
│   │   Port 3000             │    │   vw_PBI_* SQL views      │  │
│   └────────────┬────────────┘    └──────────────────────────┘  │
└────────────────┼────────────────────────────────────────────────┘
                 │ HTTP / REST (JWT Bearer)
┌────────────────▼────────────────────────────────────────────────┐
│                        API LAYER                                │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │              FastAPI 0.136  -  Port 8000                │  │
│   │                                                         │  │
│   │  /auth  /employes  /pointages  /conges  /absences       │  │
│   │  /formations  /missions  /documents  /ai  /admin        │  │
│   └───────────────────────┬─────────────────────────────────┘  │
└───────────────────────────┼─────────────────────────────────────┘
                            │ SQLAlchemy ORM
┌───────────────────────────▼─────────────────────────────────────┐
│                      DATA LAYER                                 │
│                                                                 │
│   ┌──────────────────────────────────────────────────────────┐ │
│   │         SQL Server - GestionRH_Intelligente              │ │
│   │         Windows Authentication (trusted_connection)      │ │
│   │                                                          │ │
│   │  16 tables · 200k+ pointage records · 10 years history   │ │
│   └───────────────────┬──────────────────────────────────────┘ │
└───────────────────────┼─────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────┐
│                   BACKGROUND LAYER                              │
│                                                                 │
│  APScheduler (Africa/Tunis timezone)                            │
│  ├── 07:00  Simulate morning entries (by employee profile)      │
│  ├── 18:00  Simulate exits + leave requests (seasonal)          │
│  ├── 23:00  ETL -> KPI tables + Kimball star schema (Dim/Fact)   │
│  ├── 00:00  Email digest (HTML report)                          │
│  └── Sun 02:00  AI model retrain (Random Forest)               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Tech Stack

### Backend
| Package | Version | Purpose |
|---|---|---|
| FastAPI | 0.136.1 | REST API framework |
| Uvicorn | 0.46.0 | ASGI server |
| SQLAlchemy | 2.0.49 | ORM |
| pyodbc | 5.3.0 | SQL Server driver |
| Pydantic | 2.13.4 | Request/response validation |
| python-jose | 3.5.0 | JWT tokens (HS256) |
| passlib + bcrypt | 1.7.4 / 4.0.1 | Password hashing |
| APScheduler | 3.11.2 | Cron job scheduler |
| scikit-learn | 1.8.0 | Random Forest AI model |
| pandas | 2.3.3 | Data preprocessing |
| numpy | 2.4.4 | Numerical operations |
| reportlab | 4.4.10 | PDF document generation |
| python-dotenv | 1.2.2 | Environment variables |

### Frontend
| Package | Version | Purpose |
|---|---|---|
| Next.js | 16.2.6 | React framework (App Router) |
| React | 19.2.6 | UI library |
| TypeScript | 5 | Type safety |
| Tailwind CSS | 4.3.0 | Utility CSS (via PostCSS) |
| lucide-react | 1.14.0 | Icon library |

### Database
- **Microsoft SQL Server** (local, Windows Authentication)
- **Database name:** `GestionRH_Intelligente`
- **ORM connection:** `mssql+pyodbc://localhost/GestionRH_Intelligente?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes`

### Analytics
- **Power BI Desktop** connected via SQL Server ODBC
- 9 optimized `vw_PBI_*` views (see `powerbi/views.sql`)

---

## 4. Database Schema

### 16 Tables

```
Departement ──┐
              │ 1:N
Employe ───────┤──── Utilisateur (1:1)
              │
              ├──── Pointage (daily attendance records)
              ├──── PointageLog (raw clock-in/out log)
              ├──── Absence (absence records)
              ├──── Conge (leave requests)
              ├──── Document (document requests)
              ├──── Mission (business trips)
              ├──── PresenceFormation ──── Formation
              ├──── SoldeConge (leave balance, 1:1)
              └──── AlerteIA (AI-generated alerts)

DW_KPI_Employe   (ETL output - per employee KPIs)
DW_KPI_Mensuel   (ETL output - monthly global KPIs)
AdminEmploye     (admin->employee assignment)
```

### Data Warehouse - Kimball Star Schema

Created by `powerbi/star_schema.sql`, populated by `etl/load_star.py`. Four fact tables and four dimensions; the three core dimensions (Date, Employee, Department) are **conformed** across every fact.

```
Dim_Date ──────┐
Dim_Employe ───┼──── Fact_Pointage    (grain: 1 row / employee / working day)
Dim_Departement┼──── Fact_Absence     (grain: 1 row / absence event)
               ├──── Fact_Conge       (grain: 1 row / leave request)
Dim_Formation ─┴──── Fact_Formation   (grain: 1 row / employee / training participation)
```

| Table | Type | Key | Notes |
|---|---|---|---|
| `Dim_Date` | Dimension | `date_id` (YYYYMMDD) | Calendar 2015-2027: year, quarter, month, ISO week, day, weekend flag, season |
| `Dim_Departement` | Dimension (SCD-1) | `departement_sk` IDENTITY | NK `departement_id`, name, sub-department |
| `Dim_Employe` | Dimension (SCD-1) | `employe_sk` IDENTITY | NK `employe_id`, full name, post, contract, seniority, department |
| `Dim_Formation` | Dimension (SCD-1) | `formation_sk` IDENTITY | NK `formation_id`, title, organiser, type, dates, duration |
| `Fact_Pointage` | Fact | `pointage_sk` IDENTITY | FKs to all dims; measures: `heure_entree_decimal`, `duree_travail`, `retard_minutes`; flags `est_present`, `est_retard`, `sortie_manquante` |
| `Fact_Absence` | Fact | `absence_sk` IDENTITY | FKs; `motif`, `est_justifiee`, `nb_absences`=1 |
| `Fact_Conge` | Fact | `conge_sk` IDENTITY | `date_debut_id` + `date_fin_id` -> `Dim_Date`; `type_conge`, `statut`, `nb_jours` |
| `Fact_Formation` | Fact | `presence_sk` IDENTITY | FKs to Dim_Date / Employe / Departement / Formation; `est_present`, `score`, `nb_participations`=1 |

### Key Columns

**Employe**
| Column | Type | Notes |
|---|---|---|
| employe_id | PK | |
| matricule | String(20) | Unique |
| nom / prenom | String(100) | |
| date_embauche | Date | Used to calculate seniority |
| poste | String(100) | Job title |
| type_contrat | String(50) | CDI / CDD / etc. |
| statut | String(20) | Actif / Inactif |
| departement_id | FK | -> Departement |

**Pointage** - CHECK constraint: statut ∈ {`Présent`, `En retard`, `Sortie manquante`}
| Column | Type | Notes |
|---|---|---|
| date_pointage | Date | |
| heure_entree | Time | |
| heure_sortie | Time | |
| duree_travail | Float | Hours |
| retard_minutes | Integer | Minutes late |
| statut | String(30) | Constrained |

**Utilisateur** - roles: `employe` / `rh` / `admin`

**AlerteIA** - levels: `Critique` / `Moyen` / `Info`

**Mission** - CHECK: statut ∈ {`En attente`, `Approuvée`, `Refusée`}

**Document** - CHECK: statut ∈ {`En attente`, `Approuvé`, `Refusé`}

---

## 5. Backend - API Routes

Base URL: `http://localhost:8000`

### Auth
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/login` | Public | Returns JWT token + user info |

### Employees `/employes`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/employes/` | HR/Admin | List all employees |
| POST | `/employes/` | HR/Admin | Create employee |
| GET | `/employes/{id}` | HR/Admin | Get employee by ID |
| PUT | `/employes/{id}` | HR/Admin | Update employee |
| DELETE | `/employes/{id}` | Admin | Delete employee |
| GET | `/employes/stats/overview` | HR/Admin | Global HR stats |
| GET | `/employes/departements/all` | Any | List departments |
| GET | `/employes/absences/all` | HR/Admin | All absences |
| GET | `/employes/absences/{id}` | Any | Employee absences |

### Pointage `/pointages`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/pointages/pointer` | Any | Record entry/exit |
| GET | `/pointages/today` | HR/Admin | Today's attendance |
| POST | `/pointages/periode` | HR/Admin | Attendance by period |
| GET | `/pointages/kpis/global` | HR/Admin | Global KPIs |
| GET | `/pointages/kpis/departement` | HR/Admin | KPIs by department |
| GET | `/pointages/stats/evolution` | HR/Admin | Annual evolution |
| GET | `/pointages/stats/retards` | HR/Admin | Lateness stats |
| GET | `/pointages/historique/{id}` | Any | Employee history |
| GET | `/pointages/taux/{id}` | Any | Presence rate |
| GET | `/pointages/stats/monthly-range/{id}` | Any | Last N months of attendance for one employee |

### Congés `/conges`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/conges/demande/{id}` | Any | Request leave |
| GET | `/conges/{id}` | Any | Employee leaves |
| GET | `/conges/solde/{id}` | Any | Leave balance |
| GET | `/conges/en-attente/all` | HR/Admin | Pending requests |
| PUT | `/conges/valider/{id}` | HR/Admin | Approve/reject |
| DELETE | `/conges/annuler/{conge_id}/{emp_id}` | Any | Cancel leave |
| GET | `/conges/stats/par-type` | HR/Admin | Leave count grouped by type |

### AI `/ai`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/ai/prediction-absenteisme` | HR/Admin | Predict risk for all |
| GET | `/ai/employes-a-risque` | HR/Admin | At-risk employees |
| POST | `/ai/entrainer-modele` | Admin | Retrain model |
| GET | `/ai/model-info` | HR/Admin | Last training metrics + feature importances (from `model_metrics.json`) |
| POST | `/ai/generer-alertes` | HR/Admin | Generate AI alerts |
| GET | `/ai/alertes` | HR/Admin | List alerts |
| PUT | `/ai/alertes/{id}/lue` | Any | Mark alert read |
| GET | `/ai/anomalies-pointage` | HR/Admin | Attendance anomalies |
| GET | `/ai/retards-frequents` | HR/Admin | Frequent latecomers |
| GET | `/ai/prediction/{id}` | HR/Admin | Risk for one employee |

### Admin `/admin`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/users` | Admin | List all users |
| PUT | `/admin/users/{id}/role` | Admin | Change role |
| PUT | `/admin/users/{id}/statut` | Admin | Enable/disable |
| PUT | `/admin/users/{id}/reset-password` | Admin | Reset password |
| GET | `/admin/depts` | Admin | List departments |
| POST | `/admin/depts` | Admin | Create department |
| PUT | `/admin/depts/{id}` | Admin | Update department |
| DELETE | `/admin/depts/{id}` | Admin | Delete department |
| GET | `/admin/stats` | Admin | Platform statistics |
| GET | `/admin/logs` | Admin | System logs |

### Other Routes
| Prefix | Endpoints | Description |
|---|---|---|
| `/documents` | GET list, POST request, PUT validate, GET download | Document requests + PDF |
| `/missions` | GET list, POST declare, PUT validate | Business missions |
| `/formations` | GET list, POST create, POST register | Training sessions |

---

## 6. Frontend - Pages

All pages use inline styles (no Tailwind classes), indigo palette (`#6366f1` / `#4f46e5`), dark navy sidebar (`#0f172a`), and `lucide-react` icons. Authentication via `authFetch()` which injects `Authorization: Bearer <token>`.

### Login
| Route | File | Description |
|---|---|---|
| `/` | `app/page.js` | Login form - stores JWT in `localStorage` as `inet_token` |

### Admin Portal
| Route | File | Description |
|---|---|---|
| `/admin/dashboard` | `admin/dashboard/page.tsx` | Platform stats, user counts, system health |
| `/admin/users` | `admin/users/page.tsx` | User management - roles, enable/disable, password reset |
| `/admin/depts` | `admin/depts/page.tsx` | Department CRUD with modal |
| `/admin/config` | `admin/config/page.tsx` | AI thresholds, HR parameters, scheduler config, email |
| `/admin/logs` | `admin/logs/page.tsx` | Terminal-style log viewer with auto-refresh |

### HR Portal
| Route | File | Description |
|---|---|---|
| `/hr/dashboard` | `hr/dashboard/page.tsx` | KPI cards, attendance trend, department breakdown |
| `/hr/employes` | `hr/employes/page.tsx` | Employee list with search, filters, CRUD |
| `/hr/pointage` | `hr/pointage/page.tsx` | Daily attendance table, manual entry |
| `/hr/absences` | `hr/absences/page.tsx` | Absence list, justification management |
| `/hr/validations` | `hr/validations/page.tsx` | Leave + mission approval queue |
| `/hr/alertes` | `hr/alertes/page.tsx` | AI alerts - Critique/Moyen, mark as read |
| `/hr/stats` | `hr/stats/page.tsx` | Charts - evolution, department KPIs, lateness |
| `/hr/formations` | `hr/formations/page.tsx` | Manage training sessions and attendance |
| `/hr/formations-perso` | `hr/formations-perso/page.tsx` | HR manager's own training history |
| `/hr/demandes` | `hr/demandes/page.tsx` | Document requests queue |

### Employee Portal
| Route | File | Description |
|---|---|---|
| `/employe/dashboard` | `employe/dashboard/page.tsx` | Personal stats, today's attendance, upcoming leave |
| `/employe/pointage` | `employe/pointage/page.tsx` | Own attendance history |
| `/employe/demandes` | `employe/demandes/page.tsx` | Leave requests + document requests |
| `/employe/formations` | `employe/formations/page.tsx` | Own training history + scores |
| `/employe/profil` | `employe/profil/page.tsx` | Personal profile info |

### Shared Components
| File | Description |
|---|---|
| `components/Sidebar.tsx` | HR sidebar - navigation with icons |
| `components/AdminSidebar.tsx` | Admin sidebar |
| `components/EmployeeSidebar.tsx` | Employee sidebar |
| `lib/api.ts` | `authFetch()` - wraps `fetch()` with Bearer token injection |

---

## 7. Authentication & Security

### JWT Flow
```
1. POST /auth/login  {username, password}
2. Server: bcrypt.verify(password, hash)
3. Server: create JWT {sub: str(user_id), role, exp: +8h}
4. Client: stores token in localStorage as "inet_token"
5. Client: all requests use authFetch() -> Authorization: Bearer <token>
6. Server: HTTPBearer extracts token -> jwt.decode() -> user lookup
```

### Role Guards (FastAPI dependencies)
| Dependency | Allows |
|---|---|
| `get_current_user` | Any authenticated user |
| `require_hr_or_admin` | role = "rh" or "admin" |
| `require_admin` | role = "admin" only |

### Security Measures
- Passwords hashed with **bcrypt** (via passlib)
- JWT signed with **HS256**, 8-hour expiry
- CORS restricted to `localhost:3000` only
- `sub` claim stored as string (RFC 7519 compliant)
- Minimum 8-character password on admin reset
- Server filesystem paths not exposed in API responses

---

## 8. AI Model

**Algorithm:** Random Forest Classifier (scikit-learn)

**Task:** Binary classification - is this employee at absenteeism risk? (`a_risque = 0/1`)

### Input Features (9)
| Feature | Description |
|---|---|
| `anciennete` | Years at the company |
| `nb_absences` | Total absences |
| `nb_absences_injust` | Unjustified absences |
| `nb_retards` | Number of late arrivals |
| `nb_conges` | Leave requests taken |
| `moy_heures_jour` | Average daily hours worked |
| `moy_retard_min` | Average minutes late |
| `taux_absence` | Absence rate (absences / total days) |
| `taux_retard` | Lateness rate (late / total days) |

### Target Label - Temporal Validation (primary)

To avoid the circular-labelling problem (labels derived from the same data used as features), the model uses a **temporal split**:

- **Features** are computed from the historical period **2016-2023** (`get_employe_features_periode`).
- **Labels** are derived from the *later* period **2024-2025**: an employee is labelled `a_risque = 1` if their absence rate in 2024-2025 is at or above the 75th percentile.
- Only employees present in both periods are kept (inner join on `employe_id`).

The model therefore learns to predict *future* risk from *past* behaviour, not to restate the present.

**Fallback (heuristic).** If either period has fewer than 10 employees, the model falls back to all-time heuristic labelling: `a_risque = 1` when an employee meets ≥ 2 of the four criteria `nb_absences ≥ P75`, `nb_absences_injust ≥ P75`, `taux_absence ≥ P75`, `moy_heures_jour ≤ P25`.

### Validation Methodology

The training routine (`_fit_and_evaluate`) reports three independent signals:

1. **Hold-out split (80/20, stratified)** -> accuracy, precision, recall, F1.
2. **5-fold stratified cross-validation** (when ≥ 25 samples and ≥ 5 per class) -> mean ± standard deviation of F1 and accuracy, proving the result is not a lucky split.
3. **Rule-based baseline** (`_rule_based_f1`) -> F1 of a naive "flag everyone above the 75th absence-rate percentile" rule. The Random Forest is meaningful only if it beats this baseline.

Feature importances are extracted from the trained forest. All of the above is written to `ai/models/model_metrics.json` and exposed through `GET /ai/model-info`.

### Model Config
```python
RandomForestClassifier(
    n_estimators  = 100,
    max_depth     = 4,
    min_samples_leaf = 3,
    random_state  = 42
)
```

### Output
- `probabilite`: 0-100% risk score
- `niveau`: `Critique` (>70%) or `Moyen`
- Saved as `ai/models/absenteeism_model.pkl` + `ai/models/scaler.pkl`
- Metrics + feature importances saved as `ai/models/model_metrics.json`
- Falls back to rule-based percentile scoring if insufficient data

### Anomaly Detection
A separate **Isolation Forest** (`ai/anomaly_detector.py`) flags abnormal attendance behaviour (unjustified absences, abnormal punch patterns, frequent latecomers) independently of the supervised risk model.

### Retraining
- Triggered automatically every **Sunday at 02:00** via APScheduler
- Can be triggered manually: `python notifications/scheduler.py --now-retrain`
- Sends email confirmation with accuracy and at-risk count

---

## 9. ETL Pipeline

**Location:** `etl/pipeline.py`  
**Triggered:** Daily at **23:00** by scheduler

### Steps
```
Extract  ->  Transform  ->  Load (KPI tables)  ->  Load (star schema)
```

1. **Extract** (`etl/extract.py`) - reads raw `Pointage`, `Absence`, `Conge`, `Employe` from OLTP tables
2. **Transform** (`etl/transform.py`) - calculates KPIs per employee:
   - `taux_presence`, `taux_absence`, `taux_retard`
   - `nb_pointages`, `nb_presents`, `nb_retards`, `nb_absences`
   - `total_heures`, `moy_heures_jour`, `total_retard_min`
   - `nb_conges`, `jours_conges`
3. **Load - KPI tables** (`etl/load.py`) - upserts into:
   - `DW_KPI_Employe` - one row per employee
   - `DW_KPI_Mensuel` - one row per month × department
4. **Load - star schema** (`etl/load_star.py`, `run_star_etl()`) - idempotent full refresh of the Kimball model:
   - `Dim_Date` (generated calendar 2015-2027, skipped if already up to date)
   - `Dim_Departement`, `Dim_Employe`, `Dim_Formation` (truncate-and-reload, SCD type 1)
   - `Fact_Pointage`, `Fact_Absence`, `Fact_Conge`, `Fact_Formation` (joined to dimensions by surrogate key)

   The orchestrator `etl/pipeline.py` runs all four steps in order; `powerbi/star_schema.sql` creates the DW tables once.

### Manual trigger
```powershell
.\venv\Scripts\python.exe notifications/scheduler.py --now-etl
```

---

## 10. Simulation System

Simulates realistic daily employee behavior for development and demo purposes.

### Employee Profiles
Assigned deterministically from `employe_id` (same employee always same profile):

| Profile | % of Staff | Absent Rate | Late Rate | Entry Time |
|---|---|---|---|---|
| Punctual | 30% | 2% | 3% | 7:45-8:05 |
| Normal | 40% | 7% | 12% | 7:55-8:15 |
| Often Late | 20% | 5% | 35% | 8:15-9:30 |
| High Absentee | 10% | 20% | 8% | 8:00-8:30 |

### Seasonal Patterns
| Season | Effect |
|---|---|
| Winter (Dec-Jan) | +40% absence rate, illness motifs (sick leave) |
| Summer (Jun-Aug) | 18% leave requests per day (vs 4% normal), weighted toward Annuel |
| Ramadan (auto-detected) | Shifted hours: arrive 9:00-9:30, leave 15:30-16:30 |

**Ramadan periods detected:** 2024 (Mar 11-Apr 9), 2025 (Mar 1-29), 2026 (Feb 17-Mar 17)

### Historical Backfill
```powershell
# Seed 2016 to today (2,701 workdays, ~200k records)
.\venv\Scripts\python.exe scripts/seed_history.py --start-year 2016

# Seed extras: formations, missions, documents (2016-now)
.\venv\Scripts\python.exe scripts/seed_extras.py --start-year 2016
```

**Results seeded (2016-2026):**
- Pointage records: ~200,000
- Absences: ~13,300
- Leave requests: ~14,600
- Formations: 49 sessions, ~1,800 attendance records
- Missions: 198
- Documents: 165

---

## 11. Scheduler Jobs

**Location:** `notifications/scheduler.py`  
**Timezone:** `Africa/Tunis`

| Time | Job | Description |
|---|---|---|
| Mon-Fri 07:00 | `job_simulate_entrees` | Simulate morning entries for all active employees |
| Mon-Fri 18:00 | `job_simulate_sorties` | Simulate exits + generate leave requests |
| Daily 23:00 | `job_run_etl` | ETL pipeline -> update data warehouse |
| Daily 00:00 | `job_send_email` | Build and send HTML daily digest email |
| Sunday 02:00 | `job_retrain_model` | Retrain Random Forest + send accuracy report |

### Manual Triggers
```powershell
python notifications/scheduler.py --now-entrees    # entries only
python notifications/scheduler.py --now-sorties    # exits only
python notifications/scheduler.py --now-etl        # ETL only
python notifications/scheduler.py --now-retrain    # AI retrain only
python notifications/scheduler.py --now-email      # email only
python notifications/scheduler.py --now-seed       # seed 1 year history
python notifications/scheduler.py --now-seed --seed-days 90   # last 90 days
```

### Starting the Scheduler
```powershell
.\venv\Scripts\python.exe notifications/scheduler.py
```

---

## 12. Power BI Dashboards

### Setup
1. Run `powerbi/views.sql` in SSMS against `GestionRH_Intelligente`
2. Power BI Desktop -> **Get Data -> SQL Server** -> `localhost` / `GestionRH_Intelligente`
3. Import all `vw_PBI_*` views
4. Set relationships: all views connect to `vw_PBI_Employe` on `employe_id`
5. Create `_Measures` table and paste DAX from `powerbi/dax_measures.md`

### Views Created
| View | Used By | Description |
|---|---|---|
| `vw_PBI_Employe` | All pages | Employee dimension with department, seniority |
| `vw_PBI_Pointage` | Page 2 | Enriched daily attendance with flags |
| `vw_PBI_Absence` | Page 2 | Absences with season, justified flag |
| `vw_PBI_Conge` | Page 3 | Leave requests with balance remaining |
| `vw_PBI_Formation` | Page 3 | Formation attendance with score and mention |
| `vw_PBI_Mission` | Page 4 | Missions with national/international flag |
| `vw_PBI_AlerteIA` | Page 4 | AI alerts with priority ordering |
| `vw_PBI_KPI_Mensuel` | Page 1 | Monthly KPIs per department |
| `vw_PBI_Absence_Mensuel` | Page 1+2 | Monthly absence trend |

### Dashboard Pages
| Page | Key Visuals |
|---|---|
| **Executive Overview** | KPI cards (headcount, absence %, late %, critical alerts), monthly trend line, department bar |
| **Attendance & Absences** | Presence rate area chart, monthly heatmap, justified vs unjustified stacked bar, late by dept |
| **Congés & Formations** | Leave type donut, formation participation trend, score scatter, leave balance per employee |
| **AI Alerts & Missions** | Risk employee table, alert level donut, mission map by city, top missionnaire |

**Color theme:** Indigo `#6366f1`, success `#10b981`, warning `#f59e0b`, danger `#dc2626`

---

## 13. Testing & Quality

**Location:** `tests/test_business_logic.py` - run with `pytest tests/ -v`

17 unit tests covering core business logic, with **no database dependency** (pure functions and mocked log objects):

| Test class | Count | What it covers |
|---|---|---|
| `TestCalculerJoursOuvrables` | 8 | Working-day computation for leave: same day, weekends, full week, 31-day months (regression for the date-overflow bug), month/year boundaries, full-year range |
| `TestDeterminerTypePointage` | 6 | Punch-type state machine: ENTREE -> DEBUT_PAUSE -> FIN_PAUSE -> SORTIE, and duplicate (`DOUBLON`) detection within 2 minutes / after a full day |
| `TestAIFeatures` | 3 | KPI feature maths: absence-rate computation, zero-pointage edge case, zero-lateness case |

All 17 tests pass. The suite acts as a regression guard for the two bugs fixed during the audit (the leave date-arithmetic overflow and the duplicate punch-type function).

---

## 14. Project Structure

```
GestionRH/
│
├── api/                        # FastAPI application
│   ├── deps.py                 # JWT auth dependencies (get_current_user, require_admin)
│   ├── main.py                 # App factory, CORS, router registration
│   └── routes/                 # One file per resource
│       ├── auth.py             # POST /auth/login
│       ├── admin.py            # /admin/* (admin only)
│       ├── employe.py          # /employes/*
│       ├── pointage.py         # /pointages/*
│       ├── conge.py            # /conges/*
│       ├── ai.py               # /ai/* (predictions, alerts)
│       ├── document.py         # /documents/*
│       ├── mission.py          # /missions/*
│       └── formation.py        # /formations/*
│
├── models/
│   └── models.py               # SQLAlchemy ORM - 16 tables
│
├── services/                   # Business logic layer
│   ├── employe_service.py
│   ├── pointage_service.py
│   ├── conge_service.py
│   ├── document_service.py
│   ├── formation_service.py
│   └── mission_service.py
│
├── repositories/               # DB query layer
│   ├── employe_repo.py
│   ├── pointage_repo.py
│   ├── conge_repo.py
│   ├── document_repo.py
│   ├── formation_repo.py
│   └── mission_repo.py
│
├── ai/                         # AI / ML module
│   ├── absenteeism_model.py    # Random Forest train + predict
│   ├── preprocessor.py         # Feature engineering from DB
│   ├── alert_generator.py      # Rule-based alert creation
│   ├── anomaly_detector.py     # Attendance anomaly detection
│   └── models/                 # Saved model artifacts
│       ├── absenteeism_model.pkl
│       ├── scaler.pkl
│       └── model_metrics.json  # Last training metrics + feature importances
│
├── etl/                        # Data warehouse pipeline
│   ├── pipeline.py             # Orchestrator (4 steps)
│   ├── extract.py              # Read OLTP tables
│   ├── transform.py            # Calculate KPIs
│   ├── load.py                 # Upsert into DW_KPI_*
│   └── load_star.py            # Load Kimball star schema (Dim/Fact)
│
├── demo/
│   └── simulate_day.py         # Employee simulation (profiles + seasonal patterns)
│
├── scripts/                    # One-shot utility scripts
│   ├── seed_history.py         # Backfill pointage/absence 2016->now
│   ├── seed_extras.py          # Backfill formations/missions/documents
│   ├── clean_database.py       # Wipe simulation data
│   ├── process_pointages.py    # Recalculate pointage stats
│   └── update_departments.py   # Sync department data
│
├── notifications/
│   ├── scheduler.py            # APScheduler - 5 cron jobs
│   ├── digest_builder.py       # Build daily HTML email
│   ├── email_sender.py         # SMTP email sending
│   └── env.example             # Email config template
│
├── config/
│   └── database.py             # SQLAlchemy engine + SessionLocal
│
├── powerbi/
│   ├── views.sql               # 9 CREATE VIEW statements
│   ├── star_schema.sql         # Kimball DW DDL (3 Dim + 3 Fact)
│   └── dax_measures.md         # All DAX measures by page
│
├── tests/
│   └── test_business_logic.py  # 17 unit tests (pytest, no DB)
│
├── frontend-next/              # Next.js 16 application
│   └── app/
│       ├── page.js             # Login page
│       ├── lib/api.ts          # authFetch() utility
│       ├── components/         # Sidebar components (HR, Admin, Employee)
│       ├── hr/                 # 10 HR pages
│       ├── employe/            # 5 Employee pages
│       └── admin/              # 5 Admin pages
│
├── logs/
│   ├── etl.log
│   ├── scheduler.log
│   └── seed_history.log
│
├── iNET RH.pbix                # Power BI report file
├── script.sql                  # Full DB seed (62k INSERT statements)
├── requirements.txt            # Pinned Python dependencies
├── .env                        # Environment variables (not committed)
├── .env.example                # Environment variable template
└── PROJECT.md                  # This file
```

---

## 15. How to Run

### Prerequisites
- Python 3.12+
- Node.js 20+
- SQL Server (local) with `GestionRH_Intelligente` database
- ODBC Driver 17 for SQL Server

### Backend
```powershell
# From project root
.\venv\Scripts\python.exe -m uvicorn api.main:app --reload --port 8000
```

### Frontend
```powershell
cd frontend-next
npm run dev        # starts on http://localhost:3000
```

### Scheduler (optional - runs background jobs)
```powershell
.\venv\Scripts\python.exe notifications/scheduler.py
```

### Seed Data (first time only)
```powershell
# Import base data
sqlcmd -S localhost -d GestionRH_Intelligente -E -i script.sql

# Seed 10 years of attendance history
.\venv\Scripts\python.exe scripts/seed_history.py --start-year 2016

# Seed formations, missions, documents
.\venv\Scripts\python.exe scripts/seed_extras.py --start-year 2016
```

### Power BI
```powershell
# Create all views in the DB
sqlcmd -S localhost -d GestionRH_Intelligente -E -i powerbi/views.sql
# Then open iNET RH.pbix in Power BI Desktop
```

### Default Login
| Role | Username | Password |
|---|---|---|
| Admin | (set in script.sql) | (set in script.sql) |
| HR | (set in script.sql) | (set in script.sql) |
| Employee | (set in script.sql) | (set in script.sql) |

> Passwords are bcrypt-hashed. Use `scripts/fix_passwords_inet_v2.py` to reset all to a known value.

---

*iNET RH - PFE 2025/2026 - Hachem Zenati*
