# scripts/clean_database.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unicodedata
from sqlalchemy.orm import Session
from config.database import SessionLocal
from models.models import Employe, Utilisateur
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def remove_accents(text: str) -> str:
    """Enlève les accents : é->e, à->a, etc."""
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))

def clean_name(name: str) -> str:
    """Nettoie un nom : minuscule, sans accents, sans espaces"""
    name = remove_accents(name.strip().lower())
    name = name.replace(' ', '.').replace('-', '.')
    return name

def clean_database():
    db: Session = SessionLocal()
    try:
        employes = db.query(Employe).all()
        print(f"✅ {len(employes)} employés trouvés")

        updated_emails = 0
        updated_users  = 0
        skipped        = 0

        for emp in employes:
            prenom = clean_name(emp.prenom)
            nom    = clean_name(emp.nom)

            # ── Email ──────────────────────────────────────
            new_email = f"{prenom}.{nom}@inet.tn"
            if emp.adresse_mail != new_email:
                emp.adresse_mail = new_email
                updated_emails += 1

            # ── Utilisateur ────────────────────────────────
            user: Utilisateur = emp.utilisateur
            if user:
                new_username = f"{prenom}.{nom}"
                if user.username != new_username:
                    user.username = new_username
                    updated_users += 1

                # Reset mot de passe -> inet123
                user.mot_de_passe = pwd_context.hash("inet123")
            else:
                # Créer un utilisateur s'il n'en a pas
                new_username = f"{prenom}.{nom}"
                new_user = Utilisateur(
                    employe_id   = emp.employe_id,
                    username     = new_username,
                    mot_de_passe = pwd_context.hash("inet123"),
                    role         = "employe"
                )
                db.add(new_user)
                updated_users += 1

        db.commit()

        print(f"✅ Emails mis à jour     : {updated_emails}")
        print(f"✅ Utilisateurs mis à jour: {updated_users}")
        print(f"⏭️  Ignorés               : {skipped}")
        print("🎉 Base de données nettoyée avec succès!")

    except Exception as e:
        db.rollback()
        print(f"❌ Erreur: {e}")
        raise
    finally:
        db.close()


def create_admin():
    """Créer un compte Admin si inexistant"""
    db: Session = SessionLocal()
    try:
        # Vérifie si admin existe déjà
        existing = db.query(Utilisateur).filter(
            Utilisateur.username == "admin"
        ).first()

        if existing:
            print("⚠️  Admin existe déjà!")
            return

        # Prend le premier employé comme admin (ou adapte selon ton besoin)
        first_emp = db.query(Employe).first()
        if not first_emp:
            print("❌ Aucun employé trouvé!")
            return

        admin_user = Utilisateur(
            employe_id   = first_emp.employe_id,
            username     = "admin",
            mot_de_passe = pwd_context.hash("admin123"),
            role         = "admin"
        )
        db.add(admin_user)
        db.commit()
        print("✅ Compte Admin créé!")
        print("   Username : admin")
        print("   Password : admin123")

    except Exception as e:
        db.rollback()
        print(f"❌ Erreur: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 50)
    print("🧹 NETTOYAGE BASE DE DONNÉES")
    print("=" * 50)
    clean_database()
    print()
    print("=" * 50)
    print("👤 CRÉATION COMPTE ADMIN")
    print("=" * 50)
    create_admin()