from sqlalchemy.orm import Session
from models.models import Formation, PresenceFormation
from datetime import datetime

def get_all_formations(db: Session):
    return db.query(Formation).order_by(Formation.date_debut.desc()).all()

def get_formation_by_id(db: Session, formation_id: int):
    return db.query(Formation).filter(Formation.formation_id == formation_id).first()

def create_formation(db: Session, data: dict):
    formation = Formation(
        titre          = data.get("titre"),
        date_debut     = data.get("date_debut"),
        date_fin       = data.get("date_fin"),
        organisateur   = data.get("organisateur"),
        type_formation = data.get("type_formation"),
        description    = data.get("description"),
        date_creation  = datetime.now()
    )
    db.add(formation)
    db.commit()
    db.refresh(formation)
    return formation

def get_presences_by_employe(db: Session, employe_id: int):
    return db.query(PresenceFormation).filter(PresenceFormation.employe_id == employe_id).all()

def get_presences_by_formation(db: Session, formation_id: int):
    return db.query(PresenceFormation).filter(PresenceFormation.formation_id == formation_id).all()

def inscrire_employe(db: Session, formation_id: int, employe_id: int):
    existing = db.query(PresenceFormation).filter(
        PresenceFormation.formation_id == formation_id,
        PresenceFormation.employe_id == employe_id
    ).first()
    if existing:
        return existing
    presence = PresenceFormation(
        formation_id = formation_id,
        employe_id   = employe_id,
        presence     = False
    )
    db.add(presence)
    db.commit()
    db.refresh(presence)
    return presence