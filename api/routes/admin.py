# api/routes/admin.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from config.database import get_db
from models.models import Utilisateur, Employe, Departement
from pydantic import BaseModel, Field
from typing import Optional
from typing import Literal
import glob, os
from datetime import datetime
from api.deps import require_admin

router = APIRouter()

# ─── Schemas ───────────────────────────────────────────────
# Constrain every field. Literals reject values outside the allowed set and
# length limits block oversized payloads.
class DeptCreate(BaseModel):
    nom_departement:  str = Field(min_length=1, max_length=100)
    sous_departement: Optional[str] = Field(default=None, max_length=100)

class DeptUpdate(BaseModel):
    nom_departement:  Optional[str] = Field(default=None, min_length=1, max_length=100)
    sous_departement: Optional[str] = Field(default=None, max_length=100)

class UserRoleUpdate(BaseModel):
    role: Literal["employe", "rh", "admin"]

class UserStatusUpdate(BaseModel):
    statut: Literal["Actif", "Inactif"]

class ResetPassword(BaseModel):
    new_password: str = Field(min_length=8, max_length=200)

# ─── USERS ─────────────────────────────────────────────────

@router.get("/users")
def get_all_users(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    users = (
        db.query(Utilisateur, Employe)
        .join(Employe, Utilisateur.employe_id == Employe.employe_id)
        .all()
    )
    return [
        {
            "user_id":    u.user_id,
            "username":   u.username,
            "role":       u.role,
            "employe_id": u.employe_id,
            "nom":        e.nom,
            "prenom":     e.prenom,
            "email":      e.adresse_mail,
            "statut":     e.statut,
            "departement_id": e.departement_id,
        }
        for u, e in users
    ]

@router.put("/users/{user_id}/role")
def update_user_role(user_id: int, data: UserRoleUpdate, request: Request, db: Session = Depends(get_db), current: dict = Depends(require_admin)):
    user = db.query(Utilisateur).filter(Utilisateur.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if data.role not in ["employe", "rh", "admin"]:
        raise HTTPException(status_code=400, detail="Rôle invalide")
    ancien = user.role
    user.role = data.role
    db.commit()

    # Granting admin is the single most consequential action in the system.
    from services import audit_service
    audit_service.record(
        action=audit_service.ROLE_CHANGE, actor=current,
        entite="Utilisateur", entite_id=user_id,
        cible_employe_id=user.employe_id,
        ancienne_valeur=ancien, nouvelle_valeur=data.role,
        request=request,
    )
    return {"message": "Rôle mis à jour", "role": data.role}

@router.put("/users/{user_id}/statut")
def update_user_statut(user_id: int, data: UserStatusUpdate, request: Request, db: Session = Depends(get_db), current: dict = Depends(require_admin)):
    user = db.query(Utilisateur).filter(Utilisateur.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    employe = db.query(Employe).filter(Employe.employe_id == user.employe_id).first()
    ancien = employe.statut if employe else None
    if employe:
        employe.statut = data.statut
    db.commit()

    # Deactivating an account ends someone's access — record who did it.
    from services import audit_service
    audit_service.record(
        action=audit_service.STATUS_CHANGE, actor=current,
        entite="Utilisateur", entite_id=user_id,
        cible_employe_id=user.employe_id,
        ancienne_valeur=ancien, nouvelle_valeur=data.statut,
        request=request,
    )
    return {"message": "Statut mis à jour"}

@router.put("/users/{user_id}/reset-password")
def reset_password(user_id: int, data: ResetPassword, request: Request, db: Session = Depends(get_db), current: dict = Depends(require_admin)):
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    user = db.query(Utilisateur).filter(Utilisateur.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    from services.employe_service import hash_password
    user.mot_de_passe = hash_password(data.new_password)

    # Kill every existing session for this account. A password reset is usually
    # a response to compromise — leaving the attacker's token valid for the rest
    # of its eight hours would defeat the point of resetting it.
    from datetime import datetime, timezone
    from models.models import TokenRevoke
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rev = db.query(TokenRevoke).filter(TokenRevoke.user_id == user_id).first()
    if rev:
        rev.revoked_from = now
        rev.raison = "password reset"
    else:
        db.add(TokenRevoke(user_id=user_id, revoked_from=now, raison="password reset"))

    db.commit()

    # Only that an admin reset it, never the password itself — an audit trail
    # containing credentials would be worse than no audit trail.
    from services import audit_service
    audit_service.record(
        action=audit_service.PASSWORD_RESET, actor=current,
        entite="Utilisateur", entite_id=user_id,
        cible_employe_id=user.employe_id,
        detail="password reset by administrator",
        request=request,
    )
    return {"message": "Password reset successfully"}

# ─── DEPARTEMENTS ──────────────────────────────────────────

@router.get("/depts")
def get_depts(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    depts = db.query(Departement).all()
    return [
        {
            "departement_id":   d.departement_id,
            "nom_departement":  d.nom_departement,
            "sous_departement": d.sous_departement,
            "nb_employes":      len(d.employes),
            "date_creation":    str(d.date_creation)[:10] if d.date_creation else None,
        }
        for d in depts
    ]

@router.post("/depts")
def create_dept(data: DeptCreate, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    existing = db.query(Departement).filter(
        Departement.nom_departement == data.nom_departement
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Département déjà existant")
    dept = Departement(
        nom_departement=data.nom_departement,
        sous_departement=data.sous_departement,
        date_creation=datetime.now(),
        date_modification=datetime.now(),
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return {"message": "Département créé", "departement_id": dept.departement_id}

@router.put("/depts/{dept_id}")
def update_dept(dept_id: int, data: DeptUpdate, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    dept = db.query(Departement).filter(Departement.departement_id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Département not found")
    if data.nom_departement:
        dept.nom_departement = data.nom_departement
    if data.sous_departement is not None:
        dept.sous_departement = data.sous_departement
    dept.date_modification = datetime.now()
    db.commit()
    return {"message": "Département mis à jour"}

@router.delete("/depts/{dept_id}")
def delete_dept(dept_id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    dept = db.query(Departement).filter(Departement.departement_id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Département not found")
    if dept.employes:
        raise HTTPException(
            status_code=400,
            detail=f"Impossible — {len(dept.employes)} employé(s) dans ce département"
        )
    db.delete(dept)
    db.commit()
    return {"message": "Département supprimé"}

# ─── STATS ADMIN ───────────────────────────────────────────

@router.get("/stats")
def get_admin_stats(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    from models.models import AlerteIA
    nb_users    = db.query(Utilisateur).count()
    nb_employes = db.query(Employe).filter(Employe.statut == "Actif").count()
    nb_depts    = db.query(Departement).count()
    nb_admins   = db.query(Utilisateur).filter(Utilisateur.role == "admin").count()
    nb_rh       = db.query(Utilisateur).filter(Utilisateur.role == "rh").count()
    nb_alertes  = db.query(AlerteIA).filter(AlerteIA.est_lue == False).count()
    return {
        "nb_users":    nb_users,
        "nb_employes": nb_employes,
        "nb_depts":    nb_depts,
        "nb_admins":   nb_admins,
        "nb_rh":       nb_rh,
        "nb_alertes_non_lues": nb_alertes,
    }

# ─── AUDIT TRAIL ───────────────────────────────────────────

@router.get("/audit")
def get_audit_trail(
    action: Optional[str] = None,
    employe_id: Optional[int] = None,
    jours: int = 90,
    limit: int = 200,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """Who did what, and when.

    Distinct from /logs: that reads application log files (technical diagnostics,
    rotated and eventually deleted). This is the business record of decisions —
    approvals, role changes, deletions — and is kept in the database.
    """
    from datetime import date, timedelta
    from services import audit_service
    depuis = date.today() - timedelta(days=max(1, min(jours, 3650)))
    return audit_service.query(
        db, action=action, employe_id=employe_id, depuis=depuis, limit=limit
    )


@router.get("/audit/actions")
def get_audit_actions(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    """Distinct action types present in the trail, for filtering."""
    from sqlalchemy import func
    from models.models import AuditLog
    rows = (
        db.query(AuditLog.action, func.count(AuditLog.audit_id))
        .group_by(AuditLog.action)
        .order_by(func.count(AuditLog.audit_id).desc())
        .all()
    )
    return [{"action": a, "count": c} for a, c in rows]


# ─── APPLICATION LOGS ──────────────────────────────────────

@router.get("/logs")
def get_logs(source: Optional[str] = None, _: dict = Depends(require_admin)):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logs_dir = os.path.join(BASE_DIR, "logs")
    
    log_files = glob.glob(os.path.join(logs_dir, "*.log"))
    entries = []

    for path in log_files:
        file_source = os.path.basename(path).replace(".log", "")
        if source and source.lower() not in file_source.lower():
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f.readlines()[-200:]:
                    line = line.strip()
                    if not line:
                        continue
                    entries.append({
                        "source":  file_source,
                        "message": line,
                        "file":    path,
                    })
        except Exception:
            pass

    return list(reversed(entries[-500:]))
