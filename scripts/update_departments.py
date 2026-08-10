import sys
import os
import random
import unicodedata
from sqlalchemy.orm import Session
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.database import SessionLocal
from models.models import Departement, Employe, Utilisateur
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def remove_accents(text: str) -> str:
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))

def clean_name(name: str) -> str:
    name = remove_accents(name.strip().lower())
    name = name.replace(' ', '.').replace('-', '.')
    return name

ROLES = {
    "Développement": ["Business Intelligence (BI)", "Artificial Intelligence (AI)", "Software Development", "Data Engineer", "ML Engineer", "Full-Stack Dev"],
    "Assistance": ["ERP Consultant", "Hotline Support", "Technical Support", "ERP Specialist"],
    "Administration": ["Director", "Commercial", "Human Resources (HR)", "Finance", "Deputy General Manager (DGA)"]
}

def update_database():
    db: Session = SessionLocal()
    try:
        print("1. Migration des départements...")
        # Récupérer les départements existants
        old_depts = db.query(Departement).all()
        
        # Vérifier si les 3 nouveaux départements existent
        developpement_dept = db.query(Departement).filter(Departement.nom_departement == "Développement").first()
        if not developpement_dept:
            developpement_dept = Departement(nom_departement="Développement")
            db.add(developpement_dept)
            
        assistance_dept = db.query(Departement).filter(Departement.nom_departement == "Assistance").first()
        if not assistance_dept:
            assistance_dept = Departement(nom_departement="Assistance")
            db.add(assistance_dept)
            
        administration_dept = db.query(Departement).filter(Departement.nom_departement == "Administration").first()
        if not administration_dept:
            administration_dept = Departement(nom_departement="Administration")
            db.add(administration_dept)
            
        db.commit()

        new_dept_list = {
            "Développement": developpement_dept.departement_id,
            "Assistance": assistance_dept.departement_id,
            "Administration": administration_dept.departement_id
        }
        
        print("2. Mise à jour des employés (Emails, mots de passe, poste, département)...")
        employes = db.query(Employe).all()
        
        dept_names = ["Développement", "Assistance", "Administration"]
        
        for emp in employes:
            prenom = clean_name(emp.prenom)
            nom    = clean_name(emp.nom)
            
            # --- Email ---
            emp.adresse_mail = f"{prenom}.{nom}@inet.tn"
            
            # --- Département et poste ---
            # Si c'était un boss ou admin on le met dans administration
            if emp.poste and ("Directeur" in emp.poste or "PDG" in emp.poste or "RH" in emp.poste):
                assigned_dept = "Administration"
                if "PDG" in emp.poste: emp.poste = "Deputy General Manager (DGA)"
            elif emp.poste and ("Développeur" in emp.poste or "Data" in emp.poste or "Dev" in emp.poste):
                assigned_dept = "Développement"
            else:
                assigned_dept = random.choice(dept_names)
                emp.poste = random.choice(ROLES[assigned_dept])
                
            emp.departement_id = new_dept_list[assigned_dept]
            
            # --- Utilisateur ---
            user: Utilisateur = emp.utilisateur
            if user:
                user.username = f"{prenom}.{nom}"
                user.mot_de_passe = pwd_context.hash("inet123")
                # On ajuste le role si c'est RH
                if assigned_dept == "Administration" and "HR" in emp.poste:
                    user.role = "rh"
            else:
                role_user = "rh" if ("HR" in emp.poste and assigned_dept == "Administration") else "employe"
                new_user = Utilisateur(
                    employe_id   = emp.employe_id,
                    username     = f"{prenom}.{nom}",
                    mot_de_passe = pwd_context.hash("inet123"),
                    role         = role_user
                )
                db.add(new_user)
                
        db.commit()
        
        # Supprimer les anciens départements inutilisés
        print("3. Nettoyage des anciens départements...")
        new_ids = list(new_dept_list.values())
        depts_to_delete = db.query(Departement).filter(~Departement.departement_id.in_(new_ids)).all()
        for d in depts_to_delete:
            # On vérifie qu'aucun employé n'y est
            count_emp = db.query(Employe).filter(Employe.departement_id == d.departement_id).count()
            if count_emp == 0:
                # Disable check for a sec because of cascade maybe?
                db.delete(d)
        db.commit()
        
        print("🎉 Restructuration INET terminée avec succès !")

    except Exception as e:
        db.rollback()
        print(f"❌ Erreur: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    update_database()
