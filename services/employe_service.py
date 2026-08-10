from sqlalchemy.orm import Session
from repositories import employe_repo
from models.models import Utilisateur, SoldeConge, Employe, Departement
from passlib.context import CryptContext
from datetime import datetime

# ============================================
# Password Hashing
# ============================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ============================================
# Helper - Serializer
# ============================================
def employe_to_dict(employe) -> dict:
    """Convertir un objet Employe SQLAlchemy en dict JSON-serializable"""
    if not employe:
        return None
    return {
        "employe_id"    : employe.employe_id,
        "matricule"     : employe.matricule,
        "nom"           : employe.nom,
        "prenom"        : employe.prenom,
        "adresse_mail"  : employe.adresse_mail,
        "poste"         : employe.poste,
        "type_contrat"  : employe.type_contrat,
        "statut"        : employe.statut,
        "departement_id": employe.departement_id,
        "date_embauche" : str(employe.date_embauche) if employe.date_embauche else None,
        "date_naissance": str(employe.date_naissance) if employe.date_naissance else None,
        "sexe"          : employe.sexe,
    }


# ============================================
# Service - Employe
# ============================================

def get_all_employes(db: Session):
    return employe_repo.get_all_employes(db)


def get_employe(db: Session, employe_id: int):
    employe = employe_repo.get_employe_by_id(db, employe_id)
    if not employe:
        raise ValueError(f"Employé {employe_id} introuvable")
    return employe


def create_employe(db: Session, employe_data: dict, password: str):
    """Créer un employé + son compte utilisateur"""
    existing = employe_repo.get_employe_by_matricule(db, employe_data["matricule"])
    if existing:
        raise ValueError(f"Matricule {employe_data['matricule']} déjà utilisé")

    # role lives on Utilisateur, not Employe — pop it before passing to the repo
    role = employe_data.pop("role", "employe")

    employe = employe_repo.create_employe(db, employe_data)

    username = f"{employe_data['prenom'].lower()}.{employe_data['nom'].lower()}"
    utilisateur = Utilisateur(
        employe_id   = employe.employe_id,
        username     = username,
        mot_de_passe = hash_password(password),
        role         = role,
    )
    db.add(utilisateur)

    solde = SoldeConge(
        employe_id    = employe.employe_id,
        solde_annuel  = 30,
        solde_utilise = 0,
        annee         = datetime.now().year
    )
    db.add(solde)
    db.commit()

    return employe


def update_employe(db: Session, employe_id: int, employe_data: dict):
    employe = employe_repo.update_employe(db, employe_id, employe_data)
    if not employe:
        raise ValueError(f"Employé {employe_id} introuvable")
    return employe


def delete_employe(db: Session, employe_id: int):
    employe = employe_repo.delete_employe(db, employe_id)
    if not employe:
        raise ValueError(f"Employé {employe_id} introuvable")
    return employe


def authenticate_user(db: Session, username: str, password: str):
    """
    Authentifier un utilisateur - retourne un dict JSON-serializable
    """
    # ── 1. Chercher par username ──────────────────────
    utilisateur = db.query(Utilisateur).filter(
        Utilisateur.username == username
    ).first()

    # ── 2. Si pas trouvé, chercher par email ──────────
    if not utilisateur:
        employe_by_mail = db.query(Employe).filter(
            Employe.adresse_mail == username
        ).first()
        if employe_by_mail:
            utilisateur = db.query(Utilisateur).filter(
                Utilisateur.employe_id == employe_by_mail.employe_id
            ).first()

    if not utilisateur:
        return None

    # ── 3. Vérifier le mot de passe ───────────────────
    if not verify_password(password, utilisateur.mot_de_passe):
        return None

    # ── 4. Récupérer l'employé ────────────────────────
    employe = employe_repo.get_employe_by_id(db, utilisateur.employe_id)
    if not employe:
        return None

    # ── 5. Retourner un dict propre ───────────────────
    return {
        "employe" : employe_to_dict(employe),
        "role"    : utilisateur.role,
        "user_id" : utilisateur.user_id
    }


def get_stats_employes(db: Session):
    total      = db.query(Employe).filter(Employe.statut == "Actif").count()
    total_dept = db.query(Departement).count()
    return {
        "total_employes"    : total,
        "total_departements": total_dept
    }