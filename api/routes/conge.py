from fastapi import APIRouter, Depends, HTTPException, Request
from api.deps import get_current_user, require_hr_or_admin, require_self_or_hr
from sqlalchemy.orm import Session
from config.database import get_db
from services import conge_service
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

router = APIRouter()

# ============================================
# Schemas Pydantic
# ============================================
class CongeCreate(BaseModel):
    type_conge  : Optional[str] = Field(default="Annuel", max_length=50)
    date_debut  : date
    date_fin    : date
    commentaire : Optional[str] = Field(default="", max_length=1000)

class CongeValidation(BaseModel):
    rh_id       : int = Field(gt=0)
    approuve    : bool
    commentaire : Optional[str] = Field(default="", max_length=1000)

# ============================================
# Endpoints
# ============================================

@router.get("/{employe_id}", dependencies=[Depends(require_self_or_hr)])
def get_conges_employe(employe_id: int, db: Session = Depends(get_db)):
    """Récupérer tous les congés d'un employé"""
    return conge_service.get_conges_employe(db, employe_id)


@router.get("/solde/{employe_id}", dependencies=[Depends(require_self_or_hr)])
def get_solde(employe_id: int, db: Session = Depends(get_db)):
    """Récupérer le solde de congé d'un employé"""
    return conge_service.get_solde(db, employe_id)


@router.get("/en-attente/all")
def get_en_attente(db: Session = Depends(get_db)):
    """Récupérer tous les congés en attente (vue RH)"""
    return conge_service.get_conges_en_attente(db)


@router.post("/demande/{employe_id}", dependencies=[Depends(require_self_or_hr)])
def demander_conge(
    employe_id : int,
    data       : CongeCreate,
    db         : Session = Depends(get_db)
):
    """Soumettre une demande de congé"""
    try:
        return conge_service.demander_conge(db, employe_id, data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/valider/{conge_id}")
def valider_conge(
    conge_id : int,
    data     : CongeValidation,
    request  : Request,
    db       : Session = Depends(get_db),
    current  : dict = Depends(get_current_user),
):
    """Approve or reject a leave request.

    HR and admins may decide any request. A manager may decide requests from
    their own direct reports - which is how approval actually works in a
    company, and the reason manager_id exists. Everyone else is refused.
    """
    from repositories import conge_repo as _repo
    demande = _repo.get_conge_by_id(db, conge_id)
    if not demande:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    if current["role"] not in ("rh", "admin"):
        from models.models import Employe
        demandeur = db.query(Employe).filter(
            Employe.employe_id == demande.employe_id
        ).first()
        if not demandeur or demandeur.manager_id != current.get("employe_id"):
            raise HTTPException(
                status_code=403,
                detail="You may only decide leave requests from your own team",
            )

    try:
        result = conge_service.valider_conge(
            db, conge_id, data.rh_id, data.approuve, data.commentaire
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # A rejected leave request is the decision employees dispute most often, so
    # who decided it and when has to be on record.
    from repositories import conge_repo
    from services import audit_service
    conge = conge_repo.get_conge_by_id(db, conge_id)
    audit_service.record(
        action=audit_service.LEAVE_APPROVE if data.approuve else audit_service.LEAVE_REJECT,
        actor=current,
        entite="Conge",
        entite_id=conge_id,
        cible_employe_id=getattr(conge, "employe_id", None),
        nouvelle_valeur="Approuvé" if data.approuve else "Refusé",
        detail=data.commentaire,
        request=request,
    )
    return result


@router.delete("/annuler/{conge_id}/{employe_id}", dependencies=[Depends(require_self_or_hr)])
def annuler_conge(
    conge_id   : int,
    employe_id : int,
    db         : Session = Depends(get_db)
):
    """Annuler une demande de congé"""
    try:
        return conge_service.annuler_conge(db, conge_id, employe_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats/overview")
def get_stats(db: Session = Depends(get_db)):
    """Statistiques congés pour le dashboard RH"""
    return conge_service.get_stats_conges(db)


@router.get("/stats/par-type")
def get_stats_par_type(db: Session = Depends(get_db)):
    """Leave count grouped by type - used by HR dashboard chart."""
    from models.models import Conge
    from sqlalchemy import func
    rows = (
        db.query(Conge.type_conge, func.count(Conge.conge_id))
        .group_by(Conge.type_conge)
        .all()
    )
    return [{"type": t or "Non specifie", "count": c} for t, c in rows]
