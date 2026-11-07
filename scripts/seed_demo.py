"""Seed a fresh database with a fictional company.

Creates departments, employees, user accounts and leave balances so a brand new
database (a Docker/Postgres stack, or a new client workspace) has something to
show. Run scripts/seed_history.py afterwards to backfill attendance.

    python scripts/seed_demo.py                    # 60 employees
    python scripts/seed_demo.py --employees 120
    python scripts/seed_demo.py --password Demo1234!

EVERY NAME HERE IS INVENTED. That is deliberate: a public demo must never carry
real employment records - absences, lateness and AI risk scores are personal
data, and publishing a real workforce's would be a data-protection problem and
an embarrassing thing for a prospect to discover.

Names are common Tunisian surnames and given names combined at random, so the
data reads as plausible to a local buyer without describing anybody real.
"""
import argparse
import os
import random
import sys
from datetime import date, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import SessionLocal, engine, Base
from models.models import Departement, Employe, Utilisateur, SoldeConge

# Common name components, combined at random - no real person is described.
NOMS = [
    "Ben Amor", "Trabelsi", "Gharbi", "Jelassi", "Mahjoub", "Khelifi", "Nasri",
    "Bouazizi", "Sassi", "Chaabane", "Belhaj", "Ferchichi", "Zouari", "Hamdi",
    "Karoui", "Mejri", "Ayari", "Dridi", "Guesmi", "Rekik", "Tounsi", "Baccouche",
    "Slimani", "Attia", "Charfi", "Mansouri", "Hammami", "Ouali", "Riahi", "Sfaxi",
]
PRENOMS_H = [
    "Ahmed", "Mohamed", "Ali", "Youssef", "Karim", "Bilel", "Wassim", "Nizar",
    "Sofiene", "Hatem", "Ramzi", "Anis", "Chokri", "Marouane", "Hedi", "Skander",
]
PRENOMS_F = [
    "Amira", "Ines", "Sarra", "Nour", "Rania", "Emna", "Yosra", "Hiba",
    "Mariem", "Salma", "Dorra", "Asma", "Leila", "Nesrine", "Olfa", "Syrine",
]

DEPARTEMENTS = [
    ("Direction Générale", None),
    ("Ressources Humaines", None),
    ("Finance", "Comptabilité"),
    ("Informatique", "Développement"),
    ("Informatique", "Infrastructure"),
    ("Commercial", "Ventes"),
    ("Production", "Atelier"),
    ("Logistique", "Entrepôt"),
]

POSTES = {
    "Direction Générale":  ["Directeur Général", "Assistant de Direction"],
    "Ressources Humaines": ["Responsable RH", "Chargé de Recrutement", "Gestionnaire Paie"],
    "Finance":             ["Directeur Financier", "Comptable", "Contrôleur de Gestion"],
    "Informatique":        ["Développeur", "Ingénieur Système", "Chef de Projet", "Technicien Support"],
    "Commercial":          ["Commercial", "Responsable Commercial", "Chargé de Clientèle"],
    "Production":          ["Opérateur", "Chef d'Équipe", "Responsable Production"],
    "Logistique":          ["Magasinier", "Responsable Logistique", "Cariste"],
}

CONTRATS = ["CDI", "CDI", "CDI", "CDD", "Stage"]


def _hash(password: str) -> str:
    from passlib.context import CryptContext
    return CryptContext(schemes=["bcrypt"], deprecated="auto").hash(password)


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed a fictional demo company")
    ap.add_argument("--employees", type=int, default=60)
    ap.add_argument("--password", default="Demo1234!",
                    help="password for every seeded account (demo data only)")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed, for reproducibility")
    args = ap.parse_args()

    random.seed(args.seed)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if db.query(Employe).count() > 0:
            print("This database already has employees - refusing to seed on top.")
            print("Use scripts/clean_database.py first if you want a fresh start.")
            return

        # ── Departments ──
        depts = []
        for nom, sous in DEPARTEMENTS:
            d = Departement(nom_departement=nom, sous_departement=sous)
            db.add(d)
            depts.append(d)
        db.flush()
        print(f"  {len(depts)} departments")

        # ── Employees + accounts ──
        pwd = _hash(args.password)
        today = date.today()
        used_emails, used_usernames = set(), set()
        created = 0

        for i in range(args.employees):
            dept = random.choice(depts)
            sexe = random.choice(["Homme", "Femme"])
            prenom = random.choice(PRENOMS_H if sexe == "Homme" else PRENOMS_F)
            nom = random.choice(NOMS)

            base = f"{prenom}.{nom}".lower().replace(" ", "")
            email, username, n = f"{base}@demo.tn", base, 1
            while email in used_emails or username in used_usernames:
                n += 1
                email, username = f"{base}{n}@demo.tn", f"{base}{n}"
            used_emails.add(email)
            used_usernames.add(username)

            emp = Employe(
                matricule      = f"{i + 1:05d}",
                nom            = nom.upper(),
                prenom         = prenom,
                sexe           = sexe,
                adresse_mail   = email,
                date_naissance = today - timedelta(days=random.randint(23, 60) * 365),
                date_embauche  = today - timedelta(days=random.randint(120, 8 * 365)),
                poste          = random.choice(POSTES[dept.nom_departement]),
                type_contrat   = random.choice(CONTRATS),
                statut         = "Actif",
                departement_id = dept.departement_id,
            )
            db.add(emp)
            db.flush()

            # First employee is the admin, next two are HR, rest are staff.
            role = "admin" if i == 0 else ("rh" if i in (1, 2) else "employe")
            db.add(Utilisateur(
                employe_id=emp.employe_id, username=username,
                mot_de_passe=pwd, role=role,
            ))
            db.add(SoldeConge(
                employe_id=emp.employe_id, annee=today.year,
                solde_annuel=30, solde_utilise=0,
            ))
            created += 1

        db.commit()
        print(f"  {created} employees with accounts and leave balances")

        # ── Reporting lines ──
        # One manager per department (the longest-serving there), all reporting
        # to the company head. Two levels is enough to exercise the approval
        # flow without inventing an org chart nobody asked for.
        everyone = db.query(Employe).order_by(Employe.date_embauche).all()
        head = everyone[0]
        managers = {}
        for dept in depts:
            in_dept = [e for e in everyone
                       if e.departement_id == dept.departement_id and e.employe_id != head.employe_id]
            if in_dept:
                managers[dept.departement_id] = in_dept[0]

        links = 0
        for e in everyone:
            if e.employe_id == head.employe_id:
                continue                                  # the top reports to nobody
            mgr = managers.get(e.departement_id)
            if mgr and mgr.employe_id != e.employe_id:
                e.manager_id = mgr.employe_id
                links += 1
            else:
                e.manager_id = head.employe_id            # dept heads report to the top
                links += 1
        db.commit()
        print(f"  {len(managers)} managers, {links} reporting lines")

        admin = db.query(Utilisateur).filter(Utilisateur.role == "admin").first()
        hr = db.query(Utilisateur).filter(Utilisateur.role == "rh").first()
        print("\nSign in with:")
        print(f"  admin  {admin.username}")
        print(f"  HR     {hr.username}")
        print(f"  password: {args.password}   (demo data - change it before any real use)")
        print("\nNext:")
        print("  python scripts/seed_holidays.py")
        print("  python scripts/seed_history.py --days 365")
    finally:
        db.close()


if __name__ == "__main__":
    main()
