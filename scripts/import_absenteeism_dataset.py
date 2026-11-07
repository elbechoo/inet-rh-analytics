"""Import the UCI "Absenteeism at Work" dataset into the iNET RH schema.

Why this dataset
----------------
It is real: 740 absence records from 36 employees of a Brazilian courier
company, collected 2007-2010, with the reason (ICD-coded), the day, the season,
the workload and the hours lost. It is the closest public data to what this
product actually models, which means the absenteeism model can finally be
validated against real human behaviour instead of our own simulator's rules.

Get the file
------------
    https://archive.ics.uci.edu/dataset/445/absenteeism+at+work

Download, unzip, and point this script at "Absenteeism_at_work.csv"
(semicolon-separated).

Usage
-----
    python scripts/import_absenteeism_dataset.py --file "C:\\path\\Absenteeism_at_work.csv"
    python scripts/import_absenteeism_dataset.py --file ... --dry-run
    python scripts/import_absenteeism_dataset.py --file ... --purge

`--dry-run` parses and reports without writing. `--purge` removes anything a
previous run of this script created (employees whose matricule starts with
UCI-) before importing again.
"""
import argparse
import csv
import os
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import SessionLocal
from models.models import Employe, Departement, Absence, Pointage

MATRICULE_PREFIX = "UCI-"

# ICD reason codes used by the dataset. 1-21 are ICD chapters, 22-28 are the
# company's own "light" categories. Mapped to readable motifs.
REASONS = {
    0:  ("Non renseigné", False),
    1:  ("Maladie infectieuse", True),
    2:  ("Néoplasme", True),
    3:  ("Maladie du sang", True),
    4:  ("Trouble endocrinien", True),
    5:  ("Trouble mental", True),
    6:  ("Maladie du système nerveux", True),
    7:  ("Maladie de l'œil", True),
    8:  ("Maladie de l'oreille", True),
    9:  ("Maladie circulatoire", True),
    10: ("Maladie respiratoire", True),
    11: ("Maladie digestive", True),
    12: ("Maladie de la peau", True),
    13: ("Maladie musculo-squelettique", True),
    14: ("Maladie génito-urinaire", True),
    15: ("Grossesse", True),
    16: ("Affection périnatale", True),
    17: ("Malformation congénitale", True),
    18: ("Symptôme non classé", True),
    19: ("Blessure / accident", True),
    20: ("Cause externe", True),
    21: ("Facteur de santé", True),
    22: ("Consultation de suivi", True),
    23: ("Consultation médicale", True),
    24: ("Don du sang", True),
    25: ("Examen de laboratoire", True),
    26: ("Absence non justifiée", False),
    27: ("Physiothérapie", True),
    28: ("Consultation dentaire", True),
}

# The dataset covers Jul 2007 -> Jul 2010. We map it onto recent years so the
# records sit inside the window the dashboards and the model actually query.
BASE_YEAR = date.today().year - 3


def parse_rows(path: str):
    """Read the semicolon-separated file into dicts, tolerating BOM/whitespace."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        delim = ";" if sample.count(";") >= sample.count(",") else ","
        reader = csv.DictReader(fh, delimiter=delim)
        rows = []
        for raw in reader:
            row = { (k or "").strip(): (v or "").strip() for k, v in raw.items() }
            if not row.get("ID"):
                continue
            rows.append(row)
    return rows


def to_int(v, default=0):
    try:
        return int(float(str(v).replace(",", ".")))
    except (TypeError, ValueError):
        return default


def approx_date(month: int, weekday_code: int, seq: int) -> date:
    """Build a plausible date from the dataset's month + day-of-week columns.

    The dataset gives month (1-12) and day of week (2=Mon ... 6=Fri) but no year
    or day number, so we spread records deterministically across the month and
    land them on the stated weekday.
    """
    if not 1 <= month <= 12:
        month = ((seq % 12) + 1)
    year = BASE_YEAR + (seq // 240)          # roll forward roughly per year of data
    target_wd = max(0, min(4, weekday_code - 2))   # 2->Mon ... 6->Fri
    d = date(year, month, 1)
    while d.weekday() != target_wd:
        d += timedelta(days=1)
    d += timedelta(weeks=(seq % 4))          # spread across the month
    if d.month != month:                     # keep it inside the month
        d = date(year, month, min(28, d.day))
    return d


def main() -> None:
    ap = argparse.ArgumentParser(description="Import UCI Absenteeism at Work")
    ap.add_argument("--file", required=True, help="path to Absenteeism_at_work.csv")
    ap.add_argument("--dry-run", action="store_true", help="parse and report, write nothing")
    ap.add_argument("--purge", action="store_true", help="remove a previous import first")
    ap.add_argument("--dept", default="Opérations", help="department to file the staff under")
    args = ap.parse_args()

    if not os.path.exists(args.file):
        print(f"file not found: {args.file}")
        print("Download it from https://archive.ics.uci.edu/dataset/445/absenteeism+at+work")
        sys.exit(1)

    rows = parse_rows(args.file)
    if not rows:
        print("no rows parsed - is this the right file?")
        sys.exit(1)

    by_emp = defaultdict(list)
    for i, r in enumerate(rows):
        by_emp[to_int(r.get("ID"))].append((i, r))

    total_hours = sum(to_int(r.get("Absenteeism time in hours")) for r in rows)
    print(f"parsed {len(rows)} absence records across {len(by_emp)} employees")
    print(f"total hours lost in the data: {total_hours}")

    if args.dry_run:
        sample = rows[0]
        print("\ncolumns found:")
        for k in sample: print("   ", k)
        print("\nnothing written (--dry-run).")
        return

    db = SessionLocal()
    try:
        if args.purge:
            emps = db.query(Employe).filter(Employe.matricule.like(f"{MATRICULE_PREFIX}%")).all()
            ids = [e.employe_id for e in emps]
            if ids:
                db.query(Absence).filter(Absence.employe_id.in_(ids)).delete(synchronize_session=False)
                db.query(Pointage).filter(Pointage.employe_id.in_(ids)).delete(synchronize_session=False)
                for e in emps:
                    db.delete(e)
                db.commit()
            print(f"purged {len(ids)} previously imported employees")

        dept = db.query(Departement).filter(Departement.nom_departement == args.dept).first()
        if not dept:
            dept = Departement(nom_departement=args.dept)
            db.add(dept); db.commit(); db.refresh(dept)

        created_emp = created_abs = 0
        for uci_id, records in sorted(by_emp.items()):
            matricule = f"{MATRICULE_PREFIX}{uci_id:03d}"
            emp = db.query(Employe).filter(Employe.matricule == matricule).first()
            if not emp:
                first = records[0][1]
                age = to_int(first.get("Age"), 30)
                service = to_int(first.get("Service time"), 5)
                emp = Employe(
                    matricule      = matricule,
                    nom            = f"Employé {uci_id:03d}",
                    prenom         = "UCI",
                    adresse_mail   = f"uci{uci_id:03d}@dataset.local",
                    date_embauche  = date(max(BASE_YEAR - service, 1990), 1, 15),
                    date_naissance = date(date.today().year - age, 6, 15),
                    poste          = "Courier",
                    type_contrat   = "CDI",
                    statut         = "Actif",
                    departement_id = dept.departement_id,
                )
                db.add(emp); db.commit(); db.refresh(emp)
                created_emp += 1

            for seq, r in records:
                hours = to_int(r.get("Absenteeism time in hours"))
                if hours <= 0:
                    continue                      # 0-hour rows are not absences
                code = to_int(r.get("Reason for absence"))
                motif, justified = REASONS.get(code, ("Autre", False))
                d = approx_date(to_int(r.get("Month of absence")),
                                to_int(r.get("Day of the week"), 2), seq)

                exists = db.query(Absence).filter(
                    Absence.employe_id == emp.employe_id,
                    Absence.date_absence == d,
                ).first()
                if exists:
                    continue

                db.add(Absence(
                    employe_id   = emp.employe_id,
                    date_absence = d,
                    justifiee    = justified,
                    motif        = f"{motif} ({hours}h)",
                    statut       = "Justifiée" if justified else "Non justifiée",
                ))
                created_abs += 1
            db.commit()

        print(f"\nimported: {created_emp} employees, {created_abs} absence records")
        print("These are real absences from real people - the model now has "
              "genuine behaviour to learn from.")
        print("\nNext: retrain and check whether it beats the baseline on real data:")
        print("   curl -X POST http://localhost:8000/ai/entrainer-modele-v2")
        print("   curl http://localhost:8000/ai/model-info-v2")
    finally:
        db.close()


if __name__ == "__main__":
    main()
