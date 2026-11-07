"""CSV import - let a company load its own real history.

Most SMEs already keep attendance in Excel, or have a biometric terminal that
exports CSV. This turns "we have no data yet" into "bring yours": the prospect
uploads their own file during the demo and sees their own numbers.

Two steps, deliberately:
  POST /import/preview   -> parse, guess the column mapping, report what we found
  POST /import/commit    -> write it, with the mapping the user confirmed

Nothing is written until the second call, so a bad file can never corrupt the
database.
"""
import csv
import io
from datetime import date, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from api.deps import require_hr_or_admin
from config.database import get_db
from models.models import Absence, Departement, Employe, Pointage

router = APIRouter()

MAX_BYTES = 5 * 1024 * 1024          # 5 MB is plenty for a year of punches
MAX_ROWS = 50_000

# Column-name guesses, in both languages. First match wins.
GUESSES = {
    "matricule": ["matricule", "employee id", "employee_id", "id employe", "id_employe", "badge", "code"],
    "nom":       ["nom", "last name", "lastname", "surname", "name", "employee", "employé", "employe"],
    "prenom":    ["prenom", "prénom", "first name", "firstname", "given name"],
    "date":      ["date", "jour", "day", "date_pointage", "work date", "attendance date"],
    "entree":    ["entree", "entrée", "heure_entree", "check in", "checkin", "in", "arrival", "start"],
    "sortie":    ["sortie", "heure_sortie", "check out", "checkout", "out", "departure", "end"],
    "statut":    ["statut", "status", "state", "presence", "présence"],
    "departement": ["departement", "département", "department", "service", "unit", "equipe", "équipe"],
}

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y"]
TIME_FORMATS = ["%H:%M:%S", "%H:%M", "%H.%M", "%I:%M %p", "%I:%M%p"]


def _sniff(sample: str) -> str:
    counts = {d: sample.count(d) for d in [";", ",", "\t", "|"]}
    return max(counts, key=counts.get) or ","


def _norm(s: str) -> str:
    return (s or "").strip().lower().replace("_", " ")


def _guess_mapping(headers: list[str]) -> dict:
    mapping = {}
    normalised = {_norm(h): h for h in headers}
    for field, candidates in GUESSES.items():
        for c in candidates:
            for norm_h, original in normalised.items():
                if norm_h == c or c in norm_h:
                    mapping[field] = original
                    break
            if field in mapping:
                break
    return mapping


def _parse_date(v: str) -> Optional[date]:
    v = (v or "").strip()
    if not v:
        return None
    for f in DATE_FORMATS:
        try:
            return datetime.strptime(v[:19], f).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(v).date()
    except ValueError:
        return None


def _parse_time(v: str) -> Optional[time]:
    v = (v or "").strip()
    if not v:
        return None
    for f in TIME_FORMATS:
        try:
            return datetime.strptime(v, f).time()
        except ValueError:
            continue
    return None


async def _read(file: UploadFile) -> list[dict]:
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, f"File too large (max {MAX_BYTES // 1024 // 1024} MB)")
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise HTTPException(400, "Could not decode the file - save it as UTF-8 CSV")

    delim = _sniff(text[:4096])
    rows = list(csv.DictReader(io.StringIO(text), delimiter=delim))
    if not rows:
        raise HTTPException(400, "No rows found - is the first line a header?")
    if len(rows) > MAX_ROWS:
        raise HTTPException(413, f"Too many rows (max {MAX_ROWS:,})")
    return rows


@router.post("/preview")
async def preview(file: UploadFile = File(...), _: dict = Depends(require_hr_or_admin)):
    """Parse the file, guess the mapping, and report - writes nothing."""
    rows = await _read(file)
    headers = list(rows[0].keys())
    mapping = _guess_mapping(headers)

    dates, bad_dates = [], 0
    for r in rows[:500]:
        if mapping.get("date"):
            d = _parse_date(r.get(mapping["date"], ""))
            if d: dates.append(d)
            else: bad_dates += 1

    people = set()
    key = mapping.get("matricule") or mapping.get("nom")
    if key:
        people = {(r.get(key) or "").strip() for r in rows if (r.get(key) or "").strip()}

    return {
        "filename": file.filename,
        "rows": len(rows),
        "headers": headers,
        "mapping": mapping,
        "missing": [f for f in ("date",) if f not in mapping],
        "people_detected": len(people),
        "date_range": ({"from": min(dates).isoformat(), "to": max(dates).isoformat()}
                       if dates else None),
        "unparsable_dates_in_sample": bad_dates,
        "sample": rows[:5],
    }


@router.post("/commit")
async def commit(
    file: UploadFile = File(...),
    col_matricule: Optional[str] = Form(None),
    col_nom: Optional[str] = Form(None),
    col_prenom: Optional[str] = Form(None),
    col_date: str = Form(...),
    col_entree: Optional[str] = Form(None),
    col_sortie: Optional[str] = Form(None),
    col_departement: Optional[str] = Form(None),
    create_missing_employees: bool = Form(True),
    db: Session = Depends(get_db),
    _: dict = Depends(require_hr_or_admin),
):
    """Write the rows using a confirmed column mapping."""
    rows = await _read(file)

    dept_cache: dict[str, Departement] = {}
    emp_cache: dict[str, Employe] = {}
    created_emp = created_ptg = created_abs = skipped = 0
    errors: list[str] = []

    def get_dept(name: str) -> Optional[Departement]:
        name = (name or "").strip()
        if not name:
            return None
        if name in dept_cache:
            return dept_cache[name]
        d = db.query(Departement).filter(Departement.nom_departement == name).first()
        if not d:
            d = Departement(nom_departement=name)
            db.add(d); db.commit(); db.refresh(d)
        dept_cache[name] = d
        return d

    for i, r in enumerate(rows, start=2):          # header is line 1
        try:
            d = _parse_date(r.get(col_date, ""))
            if not d:
                skipped += 1
                continue

            matricule = (r.get(col_matricule) or "").strip() if col_matricule else ""
            nom       = (r.get(col_nom) or "").strip() if col_nom else ""
            prenom    = (r.get(col_prenom) or "").strip() if col_prenom else ""
            ident     = matricule or f"{prenom} {nom}".strip()
            if not ident:
                skipped += 1
                continue

            emp = emp_cache.get(ident)
            if not emp:
                q = db.query(Employe)
                emp = (q.filter(Employe.matricule == matricule).first() if matricule
                       else q.filter(Employe.nom == nom, Employe.prenom == prenom).first())
                if not emp:
                    if not create_missing_employees:
                        skipped += 1
                        continue
                    dept = get_dept(r.get(col_departement, "")) if col_departement else None
                    emp = Employe(
                        matricule      = matricule or f"IMP-{i:05d}",
                        nom            = nom or ident,
                        prenom         = prenom or "",
                        adresse_mail   = f"{(matricule or ident).lower().replace(' ', '.')}@import.local",
                        date_embauche  = d,
                        poste          = "-",
                        type_contrat   = "CDI",
                        statut         = "Actif",
                        departement_id = dept.departement_id if dept else None,
                    )
                    db.add(emp); db.commit(); db.refresh(emp)
                    created_emp += 1
                emp_cache[ident] = emp

            t_in  = _parse_time(r.get(col_entree, "")) if col_entree else None
            t_out = _parse_time(r.get(col_sortie, "")) if col_sortie else None

            if not t_in:
                # No arrival time on a working row -> treat as an absence.
                if not db.query(Absence).filter(
                    Absence.employe_id == emp.employe_id, Absence.date_absence == d
                ).first():
                    db.add(Absence(
                        employe_id=emp.employe_id, date_absence=d,
                        justifiee=False, motif="Importé", statut="Non justifiée",
                    ))
                    created_abs += 1
                continue

            if db.query(Pointage).filter(
                Pointage.employe_id == emp.employe_id, Pointage.date_pointage == d
            ).first():
                skipped += 1
                continue

            retard = 0
            ref = time(8, 0)
            if t_in > ref:
                retard = int((datetime.combine(d, t_in) - datetime.combine(d, ref)).total_seconds() // 60)

            duree = None
            if t_out:
                duree = round(
                    (datetime.combine(d, t_out) - datetime.combine(d, t_in)).total_seconds() / 3600, 2
                )

            db.add(Pointage(
                employe_id     = emp.employe_id,
                date_pointage  = d,
                heure_entree   = t_in,
                heure_sortie   = t_out,
                duree_travail  = duree,
                retard_minutes = retard,
                statut         = "En retard" if retard > 0 else "Présent",
            ))
            created_ptg += 1

            if created_ptg % 500 == 0:
                db.commit()

        except Exception as e:                      # one bad row must not kill the import
            skipped += 1
            if len(errors) < 10:
                errors.append(f"line {i}: {e}")

    db.commit()
    return {
        "employees_created": created_emp,
        "attendance_imported": created_ptg,
        "absences_imported": created_abs,
        "skipped": skipped,
        "errors": errors,
    }
