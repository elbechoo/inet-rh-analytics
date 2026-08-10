from fastapi import APIRouter, Depends, HTTPException
from api.deps import require_hr_or_admin, require_self_or_hr
from sqlalchemy.orm import Session
from config.database import get_db
from services import mission_service
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter()

# Constrained inputs
class DeclarerMissionSchema(BaseModel):
    employe_id   : int = Field(gt=0)
    lieu         : str = Field(min_length=1, max_length=150)
    date_debut   : str = Field(min_length=1, max_length=30)
    date_fin     : str = Field(min_length=1, max_length=30)
    role         : Optional[str] = Field(default=None, max_length=100)
    type_mission : Optional[str] = Field(default=None, max_length=50)

class ValiderMissionSchema(BaseModel):
    rh_id       : int = Field(gt=0)
    approuve    : bool
    commentaire : Optional[str] = Field(default=None, max_length=1000)

@router.get("/")
def get_all_missions(db: Session = Depends(get_db)):
    return mission_service.get_all_missions(db)

@router.get("/en-attente")
def get_missions_en_attente(db: Session = Depends(get_db)):
    return mission_service.get_missions_en_attente(db)

@router.get("/employe/{employe_id}", dependencies=[Depends(require_self_or_hr)])
def get_missions_employe(employe_id: int, db: Session = Depends(get_db)):
    return mission_service.get_missions_employe(db, employe_id)

@router.post("/")
def declarer_mission(data: DeclarerMissionSchema, db: Session = Depends(get_db)):
    return mission_service.declarer_mission(db, data.employe_id, {
        "lieu"        : data.lieu,
        "date_debut"  : data.date_debut,
        "date_fin"    : data.date_fin,
        "role"        : data.role,
        "type_mission": data.type_mission
    })

@router.put("/{mission_id}/valider", dependencies=[Depends(require_hr_or_admin)])
def valider_mission(mission_id: int, data: ValiderMissionSchema, db: Session = Depends(get_db)):
    result = mission_service.valider_mission(db, mission_id, data.rh_id, data.approuve, data.commentaire)
    if not result:
        raise HTTPException(status_code=404, detail="Mission non trouvée")
    return result
