from fastapi import APIRouter, Depends
from api.deps import require_self_or_hr
from sqlalchemy.orm import Session
from sqlalchemy import case, func, text
from config.database import get_db
from services import pointage_service
from models.models import Pointage, Employe, Absence, Departement, Conge
from api.utils.cache import ttl_cache
from pydantic import BaseModel
from datetime import date, datetime, time

router = APIRouter()

# ============================================
# Schemas Pydantic
# ============================================
class PointerSchema(BaseModel):
    employe_id: int

class PeriodeSchema(BaseModel):
    employe_id : int
    date_debut : date
    date_fin   : date

# ============================================
# Endpoints — Routes fixes EN PREMIER
# ============================================

@router.post("/pointer")
def pointer(data: PointerSchema, db: Session = Depends(get_db)):
    return pointage_service.pointer(db, data.employe_id)


@router.get("/today")
def get_today(db: Session = Depends(get_db)):
    return pointage_service.get_all_today(db)


@router.post("/periode")
def get_periode(data: PeriodeSchema, db: Session = Depends(get_db)):
    return pointage_service.get_pointages_periode(
        db, data.employe_id, data.date_debut, data.date_fin
    )


@router.post("/detecter-absences")
def detecter_absences(data: PeriodeSchema, db: Session = Depends(get_db)):
    absences = pointage_service.detecter_absences(
        db, data.employe_id, data.date_debut, data.date_fin
    )
    return {
        "message"        : f"{len(absences)} absence(s) détectée(s)",
        "dates_absences" : absences
    }
@router.get("/logs/today/{employe_id}", dependencies=[Depends(require_self_or_hr)])
def get_logs_today(employe_id: int, db: Session = Depends(get_db)):
    from models.models import PointageLog
    today  = date.today()
    depuis = datetime.combine(today, time(0, 0))
    logs   = db.query(PointageLog).filter(
        PointageLog.employe_id == employe_id,
        PointageLog.timestamp_pointage >= depuis
    ).order_by(PointageLog.timestamp_pointage).all()
    return [{"type": l.type_pointage, "heure": l.timestamp_pointage.strftime("%H:%M:%S")} for l in logs]

# ============================================
# KPIs Global
# ============================================
@router.get("/kpis/global")
@ttl_cache(seconds=120, key="kpis_global")
def kpis_global(db: Session = Depends(get_db)):
    """Global KPIs — served from the pre-aggregated warehouse table.

    DW_KPI_Employe (76 rows) is rebuilt by the nightly ETL and holds every
    per-employee total we need; summing 76 rows is a couple of milliseconds
    versus the ~4 s full-scan on the OLTP Pointage table (196 k rows).
    Falls back to the OLTP path if the warehouse is empty (cold start).
    """
    try:
        # Fast path — read totals out of the warehouse in one query.
        row = db.execute(text("""
            SELECT
                COUNT(*)                    AS nb_employes,
                COALESCE(SUM(nb_pointages),  0) AS total_pointages,
                COALESCE(SUM(nb_retards),    0) AS total_retards,
                COALESCE(SUM(nb_absences),   0) AS total_absences,
                COALESCE(SUM(nb_conges),     0) AS total_conges,
                COALESCE(AVG(moy_heures_jour), 0) AS moy_heures
            FROM DW_KPI_Employe
        """)).first()

        nb_emp = int(row[0] or 0)
        if nb_emp > 0:
            total_pointages = int(row[1] or 0)
            total_retards   = int(row[2] or 0)
            total_absences  = int(row[3] or 0)
            total_conges    = int(row[4] or 0)
            moy_heures      = round(float(row[5] or 0), 2)
            denom_abs       = max(total_pointages + total_absences, 1)
            return {
                "total_employes"   : nb_emp,
                "total_pointages"  : total_pointages,
                "total_retards"    : total_retards,
                "total_absences"   : total_absences,
                "total_conges"     : total_conges,
                "moy_heures_jour"  : moy_heures,
                "taux_retard"      : round(total_retards / max(total_pointages, 1) * 100, 2),
                "taux_absenteisme" : round(total_absences / denom_abs * 100, 2),
            }

        # Cold-start fallback — warehouse not built yet, scan OLTP once.
        p_row = db.query(
            func.count(Pointage.pointage_id),
            func.sum(case((Pointage.statut == "En retard", 1), else_=0)),
            func.avg(case((Pointage.duree_travail > 0, Pointage.duree_travail))),
        ).one()
        total_pointages = int(p_row[0] or 0)
        total_retards   = int(p_row[1] or 0)
        moy_heures      = round(float(p_row[2] or 0), 2)
        total_absences  = db.query(func.count(Absence.absence_id)).scalar() or 0
        total_employes  = db.query(func.count(Employe.employe_id)) \
            .filter(Employe.statut == "Actif").scalar() or 0
        total_conges    = db.query(func.count(Conge.conge_id)) \
            .filter(Conge.statut == "Approuvé").scalar() or 0
        denom_abs       = max(total_pointages + total_absences, 1)
        return {
            "total_employes"   : total_employes,
            "total_pointages"  : total_pointages,
            "total_retards"    : total_retards,
            "total_absences"   : int(total_absences),
            "total_conges"     : total_conges,
            "moy_heures_jour"  : moy_heures,
            "taux_retard"      : round(total_retards / max(total_pointages, 1) * 100, 2),
            "taux_absenteisme" : round(total_absences / denom_abs * 100, 2),
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================
# KPIs par Département
# ============================================
@router.get("/kpis/departement")
@ttl_cache(seconds=120, key="kpis_departement")
def kpis_par_departement(db: Session = Depends(get_db)):
    """Per-department KPIs — served from the warehouse in one GROUP BY.

    DW_KPI_Employe already carries the department name on every row, so the
    whole answer is a single GROUP BY over 76 rows (typically <10 ms).
    Falls back to the OLTP path if the warehouse is empty.
    """
    try:
        rows = db.execute(text("""
            SELECT
                departement,
                COUNT(*)                       AS nb_employes,
                COALESCE(SUM(nb_pointages),0)  AS nb_pointages,
                COALESCE(SUM(nb_retards),0)    AS nb_retards,
                COALESCE(SUM(nb_absences),0)   AS nb_absences,
                COALESCE(AVG(moy_heures_jour),0) AS moy_h
            FROM DW_KPI_Employe
            WHERE departement IS NOT NULL
            GROUP BY departement
        """)).fetchall()

        if rows:
            resultats = []
            for dept, nb_emp, nb_p, nb_r, nb_a, moy_h in rows:
                if not nb_emp:
                    continue
                resultats.append({
                    "departement"     : dept,
                    "nb_employes"     : int(nb_emp),
                    "nb_pointages"    : int(nb_p),
                    "nb_retards"      : int(nb_r),
                    "nb_absences"     : int(nb_a),
                    "taux_retard"     : round(int(nb_r) / max(int(nb_p), 1) * 100, 2),
                    "taux_absenteisme": round(int(nb_a) / max(int(nb_p) + int(nb_a), 1) * 100, 2),
                    "moy_heures_jour" : round(float(moy_h or 0), 2),
                })
            return resultats

        # Cold-start fallback (warehouse empty) — original OLTP path.
        emp_rows = db.query(
            Departement.departement_id,
            Departement.nom_departement,
            func.count(Employe.employe_id),
        ).join(Employe,
               (Employe.departement_id == Departement.departement_id) &
               (Employe.statut == "Actif")) \
         .group_by(Departement.departement_id, Departement.nom_departement) \
         .all()
        ptg_rows = db.query(
            Employe.departement_id,
            func.count(Pointage.pointage_id),
            func.sum(case((Pointage.statut == "En retard", 1), else_=0)),
            func.avg(case((Pointage.duree_travail > 0, Pointage.duree_travail))),
        ).join(Employe, Employe.employe_id == Pointage.employe_id) \
         .group_by(Employe.departement_id) \
         .all()
        by_dept_ptg = {r[0]: (int(r[1] or 0), int(r[2] or 0), float(r[3] or 0)) for r in ptg_rows}
        abs_rows = db.query(
            Employe.departement_id,
            func.count(Absence.absence_id),
        ).join(Employe, Employe.employe_id == Absence.employe_id) \
         .group_by(Employe.departement_id) \
         .all()
        by_dept_abs = {r[0]: int(r[1] or 0) for r in abs_rows}
        resultats = []
        for dept_id, dept_name, nb_emp in emp_rows:
            if not nb_emp:
                continue
            nb_pointages, nb_retards, moy_h = by_dept_ptg.get(dept_id, (0, 0, 0.0))
            nb_absences = by_dept_abs.get(dept_id, 0)
            resultats.append({
                "departement"     : dept_name,
                "nb_employes"     : int(nb_emp),
                "nb_pointages"    : nb_pointages,
                "nb_retards"      : nb_retards,
                "nb_absences"     : nb_absences,
                "taux_retard"     : round(nb_retards / max(nb_pointages, 1) * 100, 2),
                "taux_absenteisme": round(nb_absences / max(nb_pointages + nb_absences, 1) * 100, 2),
                "moy_heures_jour" : round(moy_h, 2),
            })
        return resultats
    except Exception:
        return []


# ============================================
# Stats Evolution — AVANT /stats/{employe_id}
# ============================================
@router.get("/stats/evolution")
@ttl_cache(seconds=120, key="stats_evolution")
def evolution_annuelle(db: Session = Depends(get_db)):
    """Yearly presence / absence / late rates — fed by the warehouse.

    Presence + late counts come from DW_KPI_Mensuel (one tiny GROUP BY).
    Absences would also come from the warehouse, but the current monthly
    table doesn't carry that column populated, so we still hit the
    Absence OLTP table — 14 k rows with an index on date_absence, so the
    yearly GROUP BY runs in a few ms.
    """
    try:
        # Presence + retards per year, straight from the warehouse.
        ptg_by_year: dict[int, tuple[int, int]] = {}
        for y, np_, nr in db.execute(text("""
            SELECT annee,
                   COALESCE(SUM(nb_presents), 0) AS nb_presents,
                   COALESCE(SUM(nb_retards),  0) AS nb_retards
            FROM DW_KPI_Mensuel
            GROUP BY annee
        """)).fetchall():
            ptg_by_year[int(y)] = (int(np_ or 0), int(nr or 0))

        # If the warehouse is empty (cold start), fall back to OLTP.
        if not ptg_by_year:
            for y, c, r in db.query(
                func.year(Pointage.date_pointage),
                func.count(Pointage.pointage_id),
                func.sum(case((Pointage.statut == "En retard", 1), else_=0)),
            ).group_by(func.year(Pointage.date_pointage)).all():
                ptg_by_year[int(y)] = (int(c or 0), int(r or 0))

        # Absences per year — small table, fast scan.
        abs_by_year: dict[int, int] = {}
        for y, c in db.query(
            func.year(Absence.date_absence),
            func.count(Absence.absence_id),
        ).group_by(func.year(Absence.date_absence)).all():
            abs_by_year[int(y)] = int(c or 0)

        years = sorted(set(ptg_by_year) | set(abs_by_year))
        resultats = []
        for annee in years:
            nb_p, nb_r = ptg_by_year.get(annee, (0, 0))
            nb_a       = abs_by_year.get(annee, 0)
            total      = nb_p + nb_a
            if total == 0:
                continue
            resultats.append({
                "mois"          : str(annee),
                "taux_presence" : round(nb_p / max(total, 1) * 100, 1),
                "taux_absence"  : round(nb_a / max(total, 1) * 100, 1),
                "taux_retard"   : round(nb_r / max(nb_p, 1) * 100, 1),
            })
        return resultats
    except Exception:
        return []


# ============================================
# Stats Retards — AVANT /stats/{employe_id}
# ============================================
@router.get("/stats/retards")
def stats_retards(db: Session = Depends(get_db)):
    try:
        total   = db.query(Pointage).count()
        retards = db.query(Pointage).filter(Pointage.statut == "En retard").count()
        moy_ret = db.query(func.avg(Pointage.retard_minutes)).filter(Pointage.retard_minutes > 0).scalar()
        return {
            "total_pointages": total,
            "total_retards"  : retards,
            "taux_retard"    : round(retards / max(total, 1) * 100, 2),
            "moy_retard_min" : round(float(moy_ret or 0), 2),
        }
    except Exception:
        return {}


# ============================================
# Routes dynamiques — EN DERNIER
# ============================================
@router.get("/historique/{employe_id}", dependencies=[Depends(require_self_or_hr)])
def get_historique(employe_id: int, limit: int = 30, db: Session = Depends(get_db)):
    return pointage_service.get_historique(db, employe_id, limit)


@router.get("/taux/{employe_id}", dependencies=[Depends(require_self_or_hr)])
def get_taux_presence(employe_id: int, annee: int = None, mois: int = None, db: Session = Depends(get_db)):
    if not annee: annee = datetime.now().year
    if not mois:  mois  = datetime.now().month
    taux = pointage_service.get_taux_presence_mois(db, employe_id, annee, mois)
    return {"employe_id": employe_id, "taux_presence": taux}


@router.get("/stats/{employe_id}", dependencies=[Depends(require_self_or_hr)])
def get_stats_employe(employe_id: int, annee: int = None, mois: int = None, db: Session = Depends(get_db)):
    """Per-employee attendance summary — used by the employee dashboard KPI cards.

    Returns the field names the front-end actually reads (nb_presents,
    nb_retards, nb_absences, total_heures), computed over a meaningful
    window. Defaults to **year-to-date** so the cards match the order of
    magnitude shown by the 6-month chart below them. Pass `annee` and/or
    `mois` to narrow to a specific month.

    Previous bugs fixed here:
      * field-name mismatch (returned jours_presents / total_retards,
        frontend read nb_presents / nb_retards → cards always 0);
      * status comparison used "Present" while the simulator writes
        "Présent" → jours_presents was always 0 even when computed;
      * absences come from the Absence table, not Pointage — they were
        never counted.
    """
    today = date.today()
    if annee is None:
        annee = today.year
    if mois is None:
        # Year-to-date: January 1st through today.
        date_debut = date(annee, 1, 1)
        date_fin   = today if annee == today.year else date(annee, 12, 31)
    else:
        date_debut = date(annee, mois, 1)
        if mois == 12:
            date_fin = date(annee, 12, 31)
        else:
            from datetime import timedelta as _td
            date_fin = date(annee, mois + 1, 1) - _td(days=1)

    # Pointages — covers Présent + En retard + Sortie manquante.
    p_row = db.query(
        func.count(Pointage.pointage_id),
        func.sum(case((Pointage.statut.in_(["Présent", "Present", "En retard", "Sortie manquante"]), 1), else_=0)),
        func.sum(case((Pointage.statut == "En retard", 1), else_=0)),
        func.sum(case((Pointage.duree_travail > 0, Pointage.duree_travail), else_=0)),
    ).filter(
        Pointage.employe_id == employe_id,
        Pointage.date_pointage >= date_debut,
        Pointage.date_pointage <= date_fin,
    ).one()

    nb_pointages = int(p_row[0] or 0)
    nb_presents  = int(p_row[1] or 0)   # any day the employee was actually at work (incl. late)
    nb_retards   = int(p_row[2] or 0)
    total_heures = float(p_row[3] or 0)

    # Absences come from a separate table.
    nb_absences = db.query(func.count(Absence.absence_id)).filter(
        Absence.employe_id == employe_id,
        Absence.date_absence >= date_debut,
        Absence.date_absence <= date_fin,
    ).scalar() or 0

    return {
        "employe_id"   : employe_id,
        "periode"      : {"debut": date_debut.isoformat(), "fin": date_fin.isoformat()},
        "nb_pointages" : nb_pointages,
        "nb_presents"  : nb_presents,
        "nb_retards"   : nb_retards,
        "nb_absences"  : int(nb_absences),
        "total_heures" : round(total_heures, 2),
        # Backward-compatible aliases for any older caller still on the old names.
        "jours_presents": nb_presents,
        "jours_absents" : int(nb_absences),
        "total_retards" : nb_retards,
    }


@router.get("/stats/monthly-range/{employe_id}", dependencies=[Depends(require_self_or_hr)])
def get_monthly_range(employe_id: int, months: int = 6, db: Session = Depends(get_db)):
    """Last N months of attendance stats for one employee — used by employee dashboard chart."""
    import calendar
    today = date.today()
    result = []
    for i in range(months - 1, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        _, last_day = calendar.monthrange(y, m)
        first = date(y, m, 1)
        last  = date(y, m, last_day)
        nb_presents = db.query(Pointage).filter(
            Pointage.employe_id == employe_id,
            Pointage.date_pointage >= first,
            Pointage.date_pointage <= last,
        ).count()
        nb_retards = db.query(Pointage).filter(
            Pointage.employe_id == employe_id,
            Pointage.date_pointage >= first,
            Pointage.date_pointage <= last,
            Pointage.statut == "En retard",
        ).count()
        nb_absences = db.query(Absence).filter(
            Absence.employe_id == employe_id,
            Absence.date_absence >= first,
            Absence.date_absence <= last,
        ).count()
        result.append({
            "mois"    : first.strftime("%b %Y"),
            "presents": nb_presents,
            "retards" : nb_retards,
            "absences": nb_absences,
        })
    return result