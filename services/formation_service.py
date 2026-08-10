from sqlalchemy.orm import Session
from repositories import formation_repo

def formation_to_dict(f) -> dict:
    return {
        "formation_id"  : f.formation_id,
        "titre"         : f.titre,
        "date_debut"    : str(f.date_debut) if f.date_debut else None,
        "date_fin"      : str(f.date_fin) if f.date_fin else None,
        "organisateur"  : f.organisateur,
        "type_formation": f.type_formation,
        "description"   : f.description,
        "date_creation" : str(f.date_creation) if f.date_creation else None,
    }

def presence_to_dict(p) -> dict:
    return {
        "presence_id" : p.presence_id,
        "formation_id": p.formation_id,
        "employe_id"  : p.employe_id,
        "presence"    : p.presence,
        "score"       : p.score,
    }

def get_all_formations(db: Session):
    formations = formation_repo.get_all_formations(db)
    return [formation_to_dict(f) for f in formations]

def create_formation(db: Session, data: dict):
    formation = formation_repo.create_formation(db, data)
    return formation_to_dict(formation)

def get_formations_employe(db: Session, employe_id: int):
    presences = formation_repo.get_presences_by_employe(db, employe_id)
    result = []
    for p in presences:
        f = formation_repo.get_formation_by_id(db, p.formation_id)
        if f:
            d = formation_to_dict(f)
            d["presence"] = p.presence
            d["score"]    = p.score
            result.append(d)
    return result

def inscrire_employe(db: Session, formation_id: int, employe_id: int):
    presence = formation_repo.inscrire_employe(db, formation_id, employe_id)
    return presence_to_dict(presence)