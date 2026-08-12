from fastapi import APIRouter, Depends, HTTPException, Request
from api.deps import require_hr_or_admin, require_self_or_hr
from sqlalchemy.orm import Session
from config.database import get_db
from services import employe_service
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, Literal

router = APIRouter()

# Reject malformed input at the edge. A basic email pattern avoids the extra
# email-validator dependency while still blocking obviously-bad addresses.
_EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

# ============================================
# Schemas Pydantic
# ============================================
class EmployeCreate(BaseModel):
    matricule      : str = Field(min_length=1, max_length=20)
    nom            : str = Field(min_length=1, max_length=100)
    prenom         : str = Field(min_length=1, max_length=100)
    date_naissance : Optional[date] = None
    sexe           : Optional[Literal["M", "F"]] = None
    adresse_mail   : str = Field(max_length=150, pattern=_EMAIL_RE)
    date_embauche  : date
    poste          : Optional[str] = Field(default=None, max_length=100)
    type_contrat   : Optional[str] = Field(default="CDI", max_length=50)
    departement_id : int = Field(gt=0)
    role           : Literal["employe", "rh", "admin"] = "employe"
    password       : str = Field(min_length=8, max_length=200)

class EmployeUpdate(BaseModel):
    nom            : Optional[str] = Field(default=None, min_length=1, max_length=100)
    prenom         : Optional[str] = Field(default=None, min_length=1, max_length=100)
    poste          : Optional[str] = Field(default=None, max_length=100)
    type_contrat   : Optional[str] = Field(default=None, max_length=50)
    statut         : Optional[Literal["Actif", "Inactif"]] = None
    departement_id : Optional[int] = Field(default=None, gt=0)

# ============================================
# Endpoints - Routes fixes EN PREMIER !
# ============================================

# NOTE: a second /employes/login endpoint used to live here. It duplicated
# /auth/login but without the rate limit and without setting the httpOnly
# cookie, which made it a credential oracle: an authenticated user could guess
# a colleague's password indefinitely and read the result. /auth/login is the
# only authentication entry point.


@router.get("/departements/all")
def get_departements(db: Session = Depends(get_db)):
    """Récupérer tous les départements"""
    from models.models import Departement
    depts = db.query(Departement).all()
    return [{"departement_id": d.departement_id, "nom_departement": d.nom_departement} for d in depts]


@router.get("/stats/overview", dependencies=[Depends(require_hr_or_admin)])
def get_stats(db: Session = Depends(get_db)):
    """Statistiques générales"""
    return employe_service.get_stats_employes(db)


def _absence_to_dict(a) -> dict:
    return {
        "absence_id"   : a.absence_id,
        "employe_id"   : a.employe_id,
        "date_absence" : str(a.date_absence),
        "justifiee"    : a.justifiee,
        "motif"        : a.motif,
        "statut"       : a.statut,
        "date_creation": str(a.date_creation) if a.date_creation else None,
    }

@router.get("/absences/all", dependencies=[Depends(require_hr_or_admin)])
def get_absences_all(db: Session = Depends(get_db)):
    from models.models import Absence
    return [_absence_to_dict(a) for a in db.query(Absence).all()]


@router.get("/absences/periode", dependencies=[Depends(require_hr_or_admin)])
def get_absences_periode(date_debut: str, date_fin: str, db: Session = Depends(get_db)):
    from models.models import Absence
    from datetime import date as dt
    d1 = dt.fromisoformat(date_debut)
    d2 = dt.fromisoformat(date_fin)
    rows = db.query(Absence).filter(
        Absence.date_absence >= d1,
        Absence.date_absence <= d2
    ).all()
    return [_absence_to_dict(a) for a in rows]


@router.get("/absences/{employe_id}", dependencies=[Depends(require_self_or_hr)])
def get_absences_employe(employe_id: int, db: Session = Depends(get_db)):
    from models.models import Absence
    return [_absence_to_dict(a) for a in db.query(Absence).filter(Absence.employe_id == employe_id).all()]


# ============================================
# Endpoints - Routes dynamiques EN DERNIER
# ============================================

@router.get("/")
def get_all_employes(db: Session = Depends(get_db)):
    """Récupérer tous les employés actifs"""
    return employe_service.get_all_employes(db)


@router.post("/", dependencies=[Depends(require_hr_or_admin)])
def create_employe(data: EmployeCreate, request: Request, db: Session = Depends(get_db),
                   current: dict = Depends(require_hr_or_admin)):
    """Créer un nouvel employé"""
    try:
        employe_data = data.model_dump(exclude={"password", "role"})
        employe_data["role"] = data.role
        result = employe_service.create_employe(db, employe_data, data.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # This also creates a login with a role, so it is an access-granting event.
    from services import audit_service
    audit_service.record(
        action=audit_service.EMPLOYEE_CREATE, actor=current,
        entite="Employe", entite_id=(result or {}).get("employe_id"),
        cible_employe_id=(result or {}).get("employe_id"),
        nouvelle_valeur=f"{employe_data.get('prenom')} {employe_data.get('nom')} — role {data.role}",
        request=request,
    )
    return result


@router.get("/{employe_id}", dependencies=[Depends(require_self_or_hr)])
def get_employe(employe_id: int, db: Session = Depends(get_db)):
    """Récupérer un employé par ID"""
    try:
        return employe_service.get_employe(db, employe_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{employe_id}", dependencies=[Depends(require_hr_or_admin)])
def update_employe(employe_id: int, data: EmployeUpdate, request: Request,
                   db: Session = Depends(get_db),
                   current: dict = Depends(require_hr_or_admin)):
    """Mettre à jour un employé"""
    employe_data = {k: v for k, v in data.dict().items() if v is not None}
    try:
        avant = employe_service.get_employe(db, employe_id)
        avant_desc = ", ".join(
            f"{k}={getattr(avant, k, None)}" for k in employe_data if hasattr(avant, k)
        )
    except Exception:
        avant_desc = None

    try:
        result = employe_service.update_employe(db, employe_id, employe_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    from services import audit_service
    audit_service.record(
        action=audit_service.EMPLOYEE_UPDATE, actor=current,
        entite="Employe", entite_id=employe_id, cible_employe_id=employe_id,
        ancienne_valeur=avant_desc,
        nouvelle_valeur=", ".join(f"{k}={v}" for k, v in employe_data.items()),
        request=request,
    )
    return result


@router.delete("/{employe_id}", dependencies=[Depends(require_hr_or_admin)])
def delete_employe(employe_id: int, request: Request, db: Session = Depends(get_db),
                   current: dict = Depends(require_hr_or_admin)):
    """Désactiver un employé"""
    try:
        result = employe_service.delete_employe(db, employe_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Ends someone's employment record and their access with it.
    from services import audit_service
    audit_service.record(
        action=audit_service.EMPLOYEE_DELETE, actor=current,
        entite="Employe", entite_id=employe_id, cible_employe_id=employe_id,
        request=request,
    )
    return result
