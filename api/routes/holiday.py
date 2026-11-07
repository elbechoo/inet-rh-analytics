from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from api.deps import require_hr_or_admin
from config.database import get_db
from models.models import JourFerie
from services import holiday_service

router = APIRouter()

# Any authenticated user may read the calendar - employees need it to plan leave.
# Editing it changes how every leave request is counted, so writes are HR/admin.
HR_ONLY = [Depends(require_hr_or_admin)]


class HolidayIn(BaseModel):
    date_ferie: date
    nom: str = Field(min_length=1, max_length=120)
    type_ferie: str = Field(default="civil", pattern="^(civil|religieux|entreprise)$")
    chome: bool = True


class HolidayPatch(BaseModel):
    nom: Optional[str] = Field(default=None, min_length=1, max_length=120)
    type_ferie: Optional[str] = Field(default=None, pattern="^(civil|religieux|entreprise)$")
    chome: Optional[bool] = None


def _out(j: JourFerie) -> dict:
    return {
        "jour_ferie_id": j.jour_ferie_id,
        "date_ferie": j.date_ferie,
        "nom": j.nom,
        "type_ferie": j.type_ferie,
        "chome": j.chome,
    }


@router.get("/")
def list_holidays(
    year: Optional[int] = Query(default=None, ge=1900, le=2200),
    db: Session = Depends(get_db),
):
    """All holidays, optionally filtered to one year."""
    q = db.query(JourFerie)
    if year:
        q = q.filter(
            JourFerie.date_ferie >= date(year, 1, 1),
            JourFerie.date_ferie <= date(year, 12, 31),
        )
    return [_out(j) for j in q.order_by(JourFerie.date_ferie).all()]


@router.get("/years")
def list_years(db: Session = Depends(get_db)):
    """Which years already have a calendar, and how many days each."""
    rows = db.query(JourFerie.date_ferie).all()
    counts: dict[int, int] = {}
    for (d,) in rows:
        counts[d.year] = counts.get(d.year, 0) + 1
    return [{"year": y, "count": counts[y]} for y in sorted(counts)]


@router.post("/", status_code=201, dependencies=HR_ONLY)
def create_holiday(data: HolidayIn, db: Session = Depends(get_db)):
    """Add a holiday, or a company-specific closure day."""
    if db.query(JourFerie).filter(JourFerie.date_ferie == data.date_ferie).first():
        raise HTTPException(
            status_code=409,
            detail=f"{data.date_ferie} is already in the calendar. Edit it instead.",
        )
    j = JourFerie(
        date_ferie=data.date_ferie,
        nom=data.nom,
        type_ferie=data.type_ferie,
        chome=data.chome,
    )
    db.add(j)
    db.commit()
    db.refresh(j)
    return _out(j)


@router.put("/{jour_ferie_id}", dependencies=HR_ONLY)
def update_holiday(jour_ferie_id: int, data: HolidayPatch, db: Session = Depends(get_db)):
    """Correct a holiday - most often an Islamic date after the official
    moon-sighting announcement differs from the stored estimate."""
    j = db.query(JourFerie).filter(JourFerie.jour_ferie_id == jour_ferie_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Holiday not found")
    if data.nom is not None:
        j.nom = data.nom
    if data.type_ferie is not None:
        j.type_ferie = data.type_ferie
    if data.chome is not None:
        j.chome = data.chome
    db.commit()
    db.refresh(j)
    return _out(j)


@router.delete("/{jour_ferie_id}", dependencies=HR_ONLY)
def delete_holiday(jour_ferie_id: int, db: Session = Depends(get_db)):
    j = db.query(JourFerie).filter(JourFerie.jour_ferie_id == jour_ferie_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Holiday not found")
    db.delete(j)
    db.commit()
    return {"message": "Holiday removed", "date_ferie": j.date_ferie}


@router.post("/seed/{year}", dependencies=HR_ONLY)
def seed_year(year: int, db: Session = Depends(get_db)):
    """Generate the standard Tunisian calendar for one year.

    Existing dates are left untouched, so this never overwrites a correction
    already made by HR.
    """
    if not 1900 <= year <= 2200:
        raise HTTPException(status_code=400, detail="Year out of range")
    res = holiday_service.seed(db, year, year, overwrite=False)
    return {
        "year": year,
        **res,
        "message": f"{res['created']} added, {res['skipped']} already present",
    }
