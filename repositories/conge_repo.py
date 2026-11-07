from sqlalchemy.orm import Session
from models.models import Conge, SoldeConge
from datetime import datetime, date, timedelta
from typing import Optional

# ============================================
# Repository - Conge
# ============================================

def get_conges_by_employe(db: Session, employe_id: int):
    """Récupérer tous les congés d'un employé"""
    return db.query(Conge).filter(
        Conge.employe_id == employe_id
    ).order_by(Conge.date_demande.desc()).all()


def get_conge_by_id(db: Session, conge_id: int):
    """Récupérer un congé par son ID"""
    return db.query(Conge).filter(Conge.conge_id == conge_id).first()


def get_conges_en_attente(db: Session):
    """Récupérer tous les congés en attente (pour le RH)"""
    return db.query(Conge).filter(
        Conge.statut == "En attente"
    ).order_by(Conge.date_demande.asc()).all()


def get_conges_by_statut(db: Session, statut: str):
    """Récupérer les congés par statut"""
    return db.query(Conge).filter(
        Conge.statut == statut
    ).all()


def create_conge(db: Session, employe_id: int, conge_data: dict):
    """
    Créer une demande de congé
    Calcule automatiquement le nombre de jours
    """
    date_debut = conge_data["date_debut"]
    date_fin   = conge_data["date_fin"]

    # Calcul automatique du nombre de jours ouvrables (hors week-ends et fériés)
    nb_jours = _calculer_jours_ouvrables(date_debut, date_fin, db)

    conge = Conge(
        employe_id  = employe_id,
        type_conge  = conge_data.get("type_conge", "Annuel"),
        date_debut  = date_debut,
        date_fin    = date_fin,
        nb_jours    = nb_jours,
        commentaire = conge_data.get("commentaire", ""),
        statut      = "En attente"
    )
    db.add(conge)
    db.commit()
    db.refresh(conge)
    return conge


def valider_conge(db: Session, conge_id: int, rh_id: int, approuve: bool, commentaire: str = ""):
    """
    Valider ou refuser un congé
    Si approuvé -> déduire du solde
    """
    conge = get_conge_by_id(db, conge_id)
    if not conge:
        return None

    conge.statut          = "Approuvé" if approuve else "Refusé"
    conge.valide_par      = rh_id
    conge.date_validation = datetime.now()
    if commentaire:
        conge.commentaire = commentaire

    # Si approuvé -> déduire du solde de congé
    if approuve:
        _deduire_solde(db, conge.employe_id, conge.nb_jours)

    db.commit()
    db.refresh(conge)
    return conge


def _deduire_solde(db: Session, employe_id: int, nb_jours: int):
    """Déduire les jours du solde de congé"""
    solde = db.query(SoldeConge).filter(
        SoldeConge.employe_id == employe_id
    ).first()

    if solde:
        solde.solde_utilise += nb_jours
    else:
        # Créer le solde si inexistant
        solde = SoldeConge(
            employe_id    = employe_id,
            solde_annuel  = 30,
            solde_utilise = nb_jours
        )
        db.add(solde)
    db.commit()


def get_solde_conge(db: Session, employe_id: int):
    """Récupérer le solde de congé d'un employé"""
    solde = db.query(SoldeConge).filter(
        SoldeConge.employe_id == employe_id
    ).first()

    if not solde:
        # Créer solde par défaut
        solde = SoldeConge(
            employe_id    = employe_id,
            solde_annuel  = 30,
            solde_utilise = 0
        )
        db.add(solde)
        db.commit()
        db.refresh(solde)

    return {
        "solde_annuel"  : solde.solde_annuel,
        "solde_utilise" : solde.solde_utilise,
        "solde_restant" : solde.solde_annuel - solde.solde_utilise
    }


def _calculer_jours_ouvrables(date_debut: date, date_fin: date, db: Session = None) -> int:
    """
    Calculer le nombre de jours ouvrables entre deux dates.

    Exclut les week-ends et, si une session est fournie, les jours fériés -
    sinon un congé qui couvre l'Aïd serait décompté du solde de l'employé.
    Le paramètre `db` est optionnel pour rester compatible avec les appels
    existants et les tests unitaires.
    """
    feries = set()
    if db is not None:
        try:
            from services.holiday_service import holiday_dates
            feries = holiday_dates(db, date_debut, date_fin)
        except Exception:
            feries = set()      # jours fériés non configurés - on ignore

    nb_jours = 0
    current = date_debut
    while current <= date_fin:
        if current.weekday() < 5 and current not in feries:  # 0=Lundi ... 4=Vendredi
            nb_jours += 1
        current += timedelta(days=1)
    return nb_jours


def delete_conge(db: Session, conge_id: int):
    """Annuler une demande de congé (si encore en attente)"""
    conge = get_conge_by_id(db, conge_id)
    if not conge or conge.statut != "En attente":
        return None
    conge.statut = "Annulé"
    db.commit()
    return conge