from sqlalchemy.orm import Session
from repositories import mission_repo

def mission_to_dict(mission) -> dict:
    return {
        "mission_id"      : mission.mission_id,
        "employe_id"      : mission.employe_id,
        "lieu"            : mission.lieu,
        "date_debut"      : str(mission.date_debut) if mission.date_debut else None,
        "date_fin"        : str(mission.date_fin) if mission.date_fin else None,
        "role"            : mission.role,
        "type_mission"    : mission.type_mission,
        "statut"          : mission.statut,
        "date_declaration": str(mission.date_declaration) if mission.date_declaration else None,
        "valide_par"      : mission.valide_par,
    }

def get_missions_employe(db: Session, employe_id: int):
    missions = mission_repo.get_missions_by_employe(db, employe_id)
    return [mission_to_dict(m) for m in missions]

def get_all_missions(db: Session):
    missions = mission_repo.get_all_missions(db)
    return [mission_to_dict(m) for m in missions]

def get_missions_en_attente(db: Session):
    missions = mission_repo.get_missions_en_attente(db)
    return [mission_to_dict(m) for m in missions]

def declarer_mission(db: Session, employe_id: int, data: dict):
    mission = mission_repo.create_mission(
        db          = db,
        employe_id  = employe_id,
        lieu        = data.get("lieu"),
        date_debut  = data.get("date_debut"),
        date_fin    = data.get("date_fin"),
        role        = data.get("role"),
        type_mission = data.get("type_mission")
    )
    return mission_to_dict(mission)

def valider_mission(db: Session, mission_id: int, rh_id: int, approuve: bool, commentaire: str = None):
    mission = mission_repo.valider_mission(db, mission_id, rh_id, approuve, commentaire)
    return mission_to_dict(mission) if mission else None