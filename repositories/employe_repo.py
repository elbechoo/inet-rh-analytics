from sqlalchemy.orm import Session
from models.models import Employe
from datetime import datetime

# ============================================
# Repository - Employe (CRUD)
# ============================================

def get_all_employes(db: Session):
    """Récupérer tous les employés"""
    return db.query(Employe).filter(Employe.statut == "Actif").all()


def get_employe_by_id(db: Session, employe_id: int):
    """Récupérer un employé par son ID"""
    return db.query(Employe).filter(Employe.employe_id == employe_id).first()


def get_employe_by_matricule(db: Session, matricule: str):
    """Récupérer un employé par son matricule"""
    return db.query(Employe).filter(Employe.matricule == matricule).first()


def get_employes_by_departement(db: Session, departement_id: int):
    """Récupérer les employés d'un département"""
    return db.query(Employe).filter(
        Employe.departement_id == departement_id,
        Employe.statut == "Actif"
    ).all()


def create_employe(db: Session, employe_data: dict):
    """Créer un nouvel employé"""
    employe = Employe(**employe_data)
    db.add(employe)
    db.commit()
    db.refresh(employe)
    return employe


def update_employe(db: Session, employe_id: int, employe_data: dict):
    """Mettre à jour un employé"""
    employe = get_employe_by_id(db, employe_id)
    if not employe:
        return None
    for key, value in employe_data.items():
        setattr(employe, key, value)
    employe.date_modification = datetime.now()
    db.commit()
    db.refresh(employe)
    return employe


def delete_employe(db: Session, employe_id: int):
    """Désactiver un employé (soft delete)"""
    employe = get_employe_by_id(db, employe_id)
    if not employe:
        return None
    employe.statut = "Inactif"
    employe.date_modification = datetime.now()
    db.commit()
    return employe


def count_employes(db: Session):
    """Compter le nombre d'employés actifs"""
    return db.query(Employe).filter(Employe.statut == "Actif").count()