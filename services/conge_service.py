from sqlalchemy.orm import Session
from repositories import conge_repo
from datetime import datetime, date

# ============================================
# Service - Conge
# ============================================

def get_conges_employe(db: Session, employe_id: int):
    """Récupérer tous les congés d'un employé"""
    return conge_repo.get_conges_by_employe(db, employe_id)


def get_conges_en_attente(db: Session):
    """Récupérer tous les congés en attente (vue RH)"""
    return conge_repo.get_conges_en_attente(db)


def get_solde(db: Session, employe_id: int):
    """Récupérer le solde de congé"""
    return conge_repo.get_solde_conge(db, employe_id)


def demander_conge(db: Session, employe_id: int, conge_data: dict):
    """
    Soumettre une demande de congé
    Vérifie que le solde est suffisant
    """
    # Vérifier dates
    date_debut = conge_data["date_debut"]
    date_fin   = conge_data["date_fin"]

    if date_debut > date_fin:
        raise ValueError("La date de début doit être avant la date de fin")

    if date_debut < date.today():
        raise ValueError("Impossible de demander un congé dans le passé")

    # Vérifier solde suffisant (seulement pour congé annuel)
    if conge_data.get("type_conge", "Annuel") == "Annuel":
        solde = conge_repo.get_solde_conge(db, employe_id)
        from repositories.conge_repo import _calculer_jours_ouvrables
        nb_jours = _calculer_jours_ouvrables(date_debut, date_fin, db)

        if solde["solde_restant"] < nb_jours:
            raise ValueError(
                f"Solde insuffisant: {solde['solde_restant']} jours restants, "
                f"{nb_jours} jours demandés"
            )

    # Vérifier pas de chevauchement avec un congé existant
    conges_existants = conge_repo.get_conges_by_employe(db, employe_id)
    for c in conges_existants:
        if c.statut in ["En attente", "Approuvé"]:
            if not (date_fin < c.date_debut or date_debut > c.date_fin):
                raise ValueError("Chevauchement avec un congé existant")

    return conge_repo.create_conge(db, employe_id, conge_data)


def valider_conge(db: Session, conge_id: int, rh_id: int, approuve: bool, commentaire: str = ""):
    """
    Valider ou refuser une demande de congé
    """
    conge = conge_repo.get_conge_by_id(db, conge_id)
    if not conge:
        raise ValueError(f"Congé {conge_id} introuvable")

    if conge.statut != "En attente":
        raise ValueError(f"Ce congé est déjà {conge.statut}")

    return conge_repo.valider_conge(db, conge_id, rh_id, approuve, commentaire)


def annuler_conge(db: Session, conge_id: int, employe_id: int):
    """
    Annuler une demande de congé (seulement si en attente)
    """
    conge = conge_repo.get_conge_by_id(db, conge_id)
    if not conge:
        raise ValueError(f"Congé {conge_id} introuvable")

    if conge.employe_id != employe_id:
        raise ValueError("Vous ne pouvez pas annuler le congé d'un autre employé")

    if conge.statut != "En attente":
        raise ValueError(f"Impossible d'annuler un congé {conge.statut}")

    return conge_repo.delete_conge(db, conge_id)


def get_stats_conges(db: Session):
    """
    Statistiques congés pour le dashboard RH
    """
    en_attente = len(conge_repo.get_conges_en_attente(db))
    approuves  = len(conge_repo.get_conges_by_statut(db, "Approuvé"))
    refuses    = len(conge_repo.get_conges_by_statut(db, "Refusé"))

    return {
        "en_attente" : en_attente,
        "approuves"  : approuves,
        "refuses"    : refuses,
        "total"      : en_attente + approuves + refuses
    }