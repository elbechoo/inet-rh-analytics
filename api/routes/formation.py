from fastapi import APIRouter, Depends, HTTPException
from api.deps import get_current_user, require_self_or_hr
from sqlalchemy.orm import Session
from config.database import get_db
from services import formation_service
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class CreateFormationSchema(BaseModel):
    titre          : str
    date_debut     : str
    date_fin       : str
    organisateur   : Optional[str] = None
    type_formation : Optional[str] = None
    description    : Optional[str] = None

class InscrireSchema(BaseModel):
    employe_id : int

@router.get("/")
def get_all_formations(db: Session = Depends(get_db)):
    return formation_service.get_all_formations(db)

@router.get("/employe/{employe_id}", dependencies=[Depends(require_self_or_hr)])
def get_formations_employe(employe_id: int, db: Session = Depends(get_db)):
    return formation_service.get_formations_employe(db, employe_id)

@router.post("/")
def create_formation(data: CreateFormationSchema, db: Session = Depends(get_db)):
    return formation_service.create_formation(db, {
        "titre"         : data.titre,
        "date_debut"    : data.date_debut,
        "date_fin"      : data.date_fin,
        "organisateur"  : data.organisateur,
        "type_formation": data.type_formation,
        "description"   : data.description,
    })

@router.post("/{formation_id}/inscrire")
def inscrire_employe(
    formation_id: int,
    data: InscrireSchema,
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_user),
):
    """Enrol someone on a training session.

    The employee id arrives in the body, not the path, so the generic guard does
    not apply. HR may enrol anyone; an employee may only enrol themselves - the
    id they send is ignored and replaced with their own.
    """
    employe_id = data.employe_id
    if current["role"] not in ("rh", "admin"):
        employe_id = current.get("employe_id")
        if not employe_id:
            raise HTTPException(status_code=403, detail="No employee record linked to this account")

    result = formation_service.inscrire_employe(db, formation_id, employe_id)
    if not result:
        raise HTTPException(status_code=400, detail="Erreur inscription")
    return result