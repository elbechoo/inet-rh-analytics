"""
iNET RH — Extras Historical Seeder
Seeds Formation + PresenceFormation, Mission, Document from 2016 to today.
Fully idempotent — checks for existing records before inserting.

Usage:
    python scripts/seed_extras.py
    python scripts/seed_extras.py --start-year 2020
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import random
import logging
from datetime import date, timedelta, datetime

from config.database import SessionLocal
from models.models import Employe, Formation, PresenceFormation, Mission, Document, SoldeConge, Conge

# logs/ is gitignored and absent from the container image — create it rather
# than crashing, and fall back to console-only if it is not writable.
_handlers = [logging.StreamHandler()]
try:
    os.makedirs("logs", exist_ok=True)
    _handlers.append(logging.FileHandler("logs/seed_history.log", encoding="utf-8", mode="a"))
except OSError:
    pass

logging.basicConfig(
    level    = logging.INFO,
    format   = "%(asctime)s - %(levelname)s - %(message)s",
    handlers = _handlers,
)
logger = logging.getLogger(__name__)

random.seed(42)

# ─────────────────────────────────────────
# FORMATION CATALOGUE
# ─────────────────────────────────────────
FORMATIONS_CATALOGUE = [
    ("Excel Avancé",                      "Interne",       "Formateur interne"),
    ("PowerPoint & Présentation",         "Interne",       "Formateur interne"),
    ("Gestion du Temps",                  "Interne",       "Cabinet RH"),
    ("Communication Professionnelle",     "Interne",       "Cabinet RH"),
    ("Sécurité Incendie & Évacuation",    "Interne",       "Protection Civile"),
    ("Premiers Secours / SST",            "Externe",       "Croix-Rouge Algérienne"),
    ("Gestion de Projet (PMP)",           "Externe",       "Institut de Gestion"),
    ("Qualité ISO 9001",                  "Externe",       "Bureau Veritas"),
    ("Droit du Travail Algérien",         "Externe",       "Cabinet Juridique"),
    ("Leadership & Management",           "Externe",       "Centre de Formation"),
    ("Python pour Données",               "E-learning",    "Coursera"),
    ("Data Analysis avec Excel",          "E-learning",    "LinkedIn Learning"),
    ("Cybersécurité & RGPD",              "E-learning",    "ANSSI"),
    ("Intelligence Artificielle",         "E-learning",    "edX"),
    ("Bureautique Windows",               "Interne",       "Formateur interne"),
    ("Gestion des Conflits",              "Externe",       "Cabinet RH"),
    ("Relations Clients",                 "Interne",       "Formateur interne"),
    ("Comptabilité de Base",              "Externe",       "ISTA"),
    ("Environnement & Sécurité",          "Externe",       "Bureau Veritas"),
    ("Évaluation des Performances",       "Interne",       "DRH"),
    ("Anglais Professionnel",             "Externe",       "British Council"),
    ("Big Data & Analytics",              "E-learning",    "Coursera"),
    ("Power BI",                          "E-learning",    "Microsoft Learn"),
    ("Négociation Commerciale",           "Externe",       "Centre de Formation"),
    ("Management Opérationnel",           "Externe",       "Institut de Gestion"),
    ("Hygiène & Santé au Travail",        "Interne",       "Médecin du Travail"),
    ("Gestion des Stocks",                "Interne",       "Formateur interne"),
    ("Réglementation Douanière",          "Externe",       "Direction des Douanes"),
    ("Marketing Digital",                 "E-learning",    "HubSpot Academy"),
    ("Ressources Humaines Stratégiques",  "Externe",       "Cabinet RH"),
]

DESCRIPTIONS = [
    "Session de formation pour renforcer les compétences professionnelles.",
    "Atelier pratique avec exercices et mises en situation réelles.",
    "Formation interactive animée par un expert du domaine.",
    "Module e-learning avec évaluation finale et certificat.",
    "Session obligatoire pour tous les employés concernés.",
    "Formation de perfectionnement et mise à niveau.",
]

# ─────────────────────────────────────────
# MISSION DATA
# ─────────────────────────────────────────
VILLES_ALGERIE = [
    "Alger", "Oran", "Constantine", "Annaba", "Sétif",
    "Tizi-Ouzou", "Béjaïa", "Blida", "Tlemcen", "Batna",
    "Biskra", "Skikda", "Chlef", "Mostaganem", "Médéa",
]
VILLES_INTERNATIONAL = ["Paris", "Lyon", "Tunis", "Casablanca", "Dubaï"]

TYPES_MISSION = ["Commercial", "Technique", "Formation", "Audit", "Inspection", "Réunion"]
ROLES_MISSION = [
    "Responsable de mission", "Expert technique", "Chargé de projet",
    "Auditeur", "Formateur", "Représentant commercial",
]

# ─────────────────────────────────────────
# DOCUMENT DATA
# ─────────────────────────────────────────
TYPES_DOCUMENT = [
    "Attestation de travail",
    "Attestation de salaire",
    "Fiche de paie",
    "Certificat de présence",
    "Ordre de mission",
    "Attestation de congé",
]


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def rand_date_in_year(year: int, month_start: int = 1, month_end: int = 12) -> date:
    start = date(year, month_start, 1)
    if month_end == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month_end + 1, 1) - timedelta(days=1)
    end = min(end, date.today() - timedelta(days=1))
    if start >= end:
        return start
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def skip_weekend(d: date) -> date:
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


# ─────────────────────────────────────────
# SEED FORMATIONS
# ─────────────────────────────────────────
def seed_formations(db, employes: list, start_year: int) -> int:
    today      = date.today()
    created    = 0

    # Existing formation titles to avoid duplicates on re-run
    existing = {f.titre + str(f.date_debut.year)
                for f in db.query(Formation.titre, Formation.date_debut).all()}

    for year in range(start_year, today.year + 1):
        # 3-5 formations per year
        nb = random.randint(3, 5)
        chosen = random.sample(FORMATIONS_CATALOGUE, nb)

        for (titre, type_f, organisateur) in chosen:
            key = titre + str(year)
            if key in existing:
                continue

            date_debut = skip_weekend(rand_date_in_year(year))
            duree      = random.randint(1, 5)  # 1-5 days
            date_fin   = date_debut + timedelta(days=duree - 1)
            if date_fin > today - timedelta(days=1):
                date_fin = date_debut

            formation = Formation(
                titre          = titre,
                date_debut     = date_debut,
                date_fin       = date_fin,
                organisateur   = organisateur,
                type_formation = type_f,
                description    = random.choice(DESCRIPTIONS),
            )
            db.add(formation)
            db.flush()

            # Assign 40-80% of employees
            nb_participants = int(len(employes) * random.uniform(0.40, 0.80))
            participants    = random.sample(employes, nb_participants)

            for emp in participants:
                # Check if this employee already has this formation
                exists = db.query(PresenceFormation).filter(
                    PresenceFormation.formation_id == formation.formation_id,
                    PresenceFormation.employe_id   == emp.employe_id,
                ).first()
                if exists:
                    continue

                attended = random.random() < 0.88  # 88% actually show up
                score    = round(random.uniform(60, 100), 1) if attended else None
                db.add(PresenceFormation(
                    formation_id = formation.formation_id,
                    employe_id   = emp.employe_id,
                    presence     = attended,
                    score        = score,
                ))

            existing.add(key)
            created += 1

    db.commit()
    return created


# ─────────────────────────────────────────
# SEED MISSIONS
# ─────────────────────────────────────────
def seed_missions(db, employes: list, start_year: int) -> int:
    today   = date.today()
    created = 0

    # Approximate existing count to avoid full duplicate scan
    existing_count = db.query(Mission).count()
    # Build a set of (employe_id, date_debut) to deduplicate
    existing_keys = {
        (m.employe_id, m.date_debut)
        for m in db.query(Mission.employe_id, Mission.date_debut).all()
    }

    for year in range(start_year, today.year + 1):
        # 15-25 missions per year across all employees
        nb = random.randint(15, 25)

        for _ in range(nb):
            emp        = random.choice(employes)
            date_debut = skip_weekend(rand_date_in_year(year))
            duree      = random.randint(1, 7)
            date_fin   = date_debut + timedelta(days=duree - 1)

            if date_fin >= today:
                continue

            key = (emp.employe_id, date_debut)
            if key in existing_keys:
                continue

            # Older missions are mostly approved; recent ones mixed
            days_ago = (today - date_debut).days
            if days_ago > 30:
                statut = random.choices(
                    ["Approuvée", "Refusée"],
                    weights=[85, 15]
                )[0]
            else:
                statut = random.choices(
                    ["En attente", "Approuvée", "Refusée"],
                    weights=[50, 40, 10]
                )[0]

            international = random.random() < 0.08
            lieu = random.choice(VILLES_INTERNATIONAL if international else VILLES_ALGERIE)

            db.add(Mission(
                employe_id      = emp.employe_id,
                lieu            = lieu,
                date_debut      = date_debut,
                date_fin        = date_fin,
                role            = random.choice(ROLES_MISSION),
                type_mission    = random.choice(TYPES_MISSION),
                statut          = statut,
                date_declaration= datetime.combine(date_debut - timedelta(days=random.randint(1, 7)), datetime.min.time()),
            ))
            existing_keys.add(key)
            created += 1

    db.commit()
    return created


# ─────────────────────────────────────────
# SEED DOCUMENTS
# ─────────────────────────────────────────
def seed_documents(db, employes: list, start_year: int) -> int:
    today   = date.today()
    created = 0

    existing_keys = {
        (d.employe_id, d.type_document, d.date_demande.year if d.date_demande else 0)
        for d in db.query(Document.employe_id, Document.type_document, Document.date_demande).all()
    }

    for year in range(start_year, today.year + 1):
        # ~20% of employees request at least one document per year
        nb_requesters = max(1, int(len(employes) * 0.20))
        requesters    = random.sample(employes, nb_requesters)

        for emp in requesters:
            type_doc = random.choice(TYPES_DOCUMENT)
            key      = (emp.employe_id, type_doc, year)
            if key in existing_keys:
                continue

            req_date = rand_date_in_year(year)
            if req_date >= today:
                continue

            days_ago = (today - req_date).days
            if days_ago > 14:
                statut = random.choices(
                    ["Approuvé", "Refusé"],
                    weights=[90, 10]
                )[0]
            else:
                statut = random.choices(
                    ["En attente", "Approuvé"],
                    weights=[60, 40]
                )[0]

            val_date = None
            if statut in ("Approuvé", "Refusé"):
                val_date = datetime.combine(
                    req_date + timedelta(days=random.randint(1, 5)),
                    datetime.min.time()
                )

            db.add(Document(
                employe_id      = emp.employe_id,
                type_document   = type_doc,
                titre           = type_doc,
                date_demande    = datetime.combine(req_date, datetime.min.time()),
                date_validation = val_date,
                statut          = statut,
                commentaire     = "Demande traitée" if statut == "Approuvé" else None,
            ))
            existing_keys.add(key)
            created += 1

    db.commit()
    return created


# ─────────────────────────────────────────
# UPDATE SOLDE CONGE
# ─────────────────────────────────────────
def update_solde_conge(db, employes: list) -> int:
    today   = date.today()
    updated = 0

    for emp in employes:
        solde = db.query(SoldeConge).filter(SoldeConge.employe_id == emp.employe_id).first()
        if not solde:
            continue

        # Count approved congés for current year
        jours_utilises = db.query(Conge).filter(
            Conge.employe_id  == emp.employe_id,
            Conge.statut      == "En attente",   # approved or pending
            Conge.date_debut  >= date(today.year, 1, 1),
            Conge.date_fin    <= today,
        ).with_entities(Conge.nb_jours).all()

        total = sum(j[0] or 0 for j in jours_utilises)
        solde.solde_utilise = min(total, solde.solde_annuel)
        solde.annee         = today.year
        updated += 1

    db.commit()
    return updated


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def seed_extras(start_year: int) -> None:
    today = date.today()
    logger.info("=" * 60)
    logger.info("iNET RH — EXTRAS SEEDER")
    logger.info(f"Period : {start_year}-01-01 → {today}")
    logger.info("=" * 60)

    db = SessionLocal()
    try:
        employes = db.query(Employe).filter(Employe.statut == "Actif").all()
        logger.info(f"Active employees : {len(employes)}")

        logger.info("Seeding Formations + Presences...")
        nb_formations = seed_formations(db, employes, start_year)
        logger.info(f"  Formations created : {nb_formations}")

        logger.info("Seeding Missions...")
        nb_missions = seed_missions(db, employes, start_year)
        logger.info(f"  Missions created   : {nb_missions}")

        logger.info("Seeding Documents...")
        nb_documents = seed_documents(db, employes, start_year)
        logger.info(f"  Documents created  : {nb_documents}")

        logger.info("Updating SoldeConge...")
        nb_soldes = update_solde_conge(db, employes)
        logger.info(f"  Soldes updated     : {nb_soldes}")

        logger.info("=" * 60)
        logger.info("EXTRAS SEED COMPLETE")
        logger.info(f"  Formations    : {nb_formations}")
        logger.info(f"  Missions      : {nb_missions}")
        logger.info(f"  Documents     : {nb_documents}")
        logger.info(f"  Soldes updated: {nb_soldes}")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.info("Seeder interrupted — partial data already committed.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed extras historical data (formations, missions, documents)")
    parser.add_argument("--start-year", type=int, default=2016, metavar="YEAR",
                        help="Start year (default: 2016)")
    args = parser.parse_args()
    seed_extras(args.start_year)
