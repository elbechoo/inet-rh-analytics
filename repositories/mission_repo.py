from sqlalchemy.orm import Session
from models.models import Mission
from datetime import datetime

def get_missions_by_employe(db: Session, employe_id: int):
    return db.query(Mission).filter(Mission.employe_id == employe_id).order_by(Mission.date_declaration.desc()).all()

def get_all_missions(db: Session):
    return db.query(Mission).order_by(Mission.date_declaration.desc()).all()

def get_missions_en_attente(db: Session):
    return db.query(Mission).filter(Mission.statut == "En attente").order_by(Mission.date_declaration.desc()).all()

def get_mission_by_id(db: Session, mission_id: int):
    return db.query(Mission).filter(Mission.mission_id == mission_id).first()

def create_mission(db: Session, employe_id: int, lieu: str, date_debut, date_fin, role: str, type_mission: str):
    mission = Mission(
        employe_id       = employe_id,
        lieu             = lieu,
        date_debut       = date_debut,
        date_fin         = date_fin,
        role             = role,
        type_mission     = type_mission,
        statut           = "En attente",
        date_declaration = datetime.now()
    )
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return mission

def valider_mission(db: Session, mission_id: int, rh_id: int, approuve: bool, commentaire: str = None):
    mission = db.query(Mission).filter(Mission.mission_id == mission_id).first()
    if not mission:
        return None
    mission.statut    = "Approuvée" if approuve else "Refusée"
    mission.valide_par = rh_id
    db.commit()
    db.refresh(mission)
    return mission