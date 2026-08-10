"""
Script pour traiter les PointageLogs et remplir la table Pointage
À exécuter une fois pour initialiser les données
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import SessionLocal
from models.models import PointageLog, Pointage, Employe
from datetime import datetime, date, timedelta, time

# Heure normale d'entrée
HEURE_NORMALE = time(8, 0)
SEUIL_RETARD  = 15  # minutes

def process_all_pointages():
    db = SessionLocal()
    try:
        print("🔄 Traitement des pointages en cours...")

        # Récupérer tous les logs
        logs = db.query(PointageLog).order_by(
            PointageLog.employe_id,
            PointageLog.timestamp_pointage
        ).all()

        if not logs:
            print("❌ Aucun log trouvé")
            return

        print(f"📊 {len(logs)} logs trouvés")

        # Grouper par employé et par date
        logs_par_emp_date = {}
        for log in logs:
            ts    = log.timestamp_pointage
            jour  = ts.date()
            key   = (log.employe_id, jour)
            if key not in logs_par_emp_date:
                logs_par_emp_date[key] = []
            logs_par_emp_date[key].append(log)

        print(f"📅 {len(logs_par_emp_date)} jours de pointage à traiter")

        nb_traites = 0

        for (emp_id, jour), logs_jour in logs_par_emp_date.items():
            # Trier par timestamp
            logs_jour.sort(key=lambda x: x.timestamp_pointage)

            # Séparer ENTREE et SORTIE
            entrees = [l for l in logs_jour if l.type_pointage == "ENTREE"]
            sorties = [l for l in logs_jour if l.type_pointage == "SORTIE"]

            # Calculer durée totale
            duree_totale = timedelta(0)
            for i, entree in enumerate(entrees):
                if i < len(sorties):
                    diff = sorties[i].timestamp_pointage - entree.timestamp_pointage
                    if diff.total_seconds() > 0:
                        duree_totale += diff

            # Heure entrée/sortie
            heure_entree = entrees[0].timestamp_pointage.time() if entrees else None
            heure_sortie = sorties[-1].timestamp_pointage.time() if sorties else None
            duree_heures = round(duree_totale.total_seconds() / 3600, 2)

            # Calcul retard
            retard_minutes = 0
            if heure_entree:
                entree_dt  = datetime.combine(jour, heure_entree)
                normale_dt = datetime.combine(jour, HEURE_NORMALE)
                if entree_dt > normale_dt:
                    retard_minutes = int((entree_dt - normale_dt).total_seconds() / 60)

            # Statut
            sortie_manquante = len(entrees) > len(sorties)
            if sortie_manquante and duree_heures == 0:
                statut = "Sortie manquante"
            elif retard_minutes > SEUIL_RETARD:
                statut = "En retard"
            elif duree_heures > 0:
                statut = "Present"
            else:
                statut = "Absent"

            # Vérifier si pointage existe déjà
            existing = db.query(Pointage).filter(
                Pointage.employe_id   == emp_id,
                Pointage.date_pointage == jour
            ).first()

            if existing:
                existing.heure_entree   = heure_entree
                existing.heure_sortie   = heure_sortie
                existing.duree_travail  = duree_heures
                existing.retard_minutes = retard_minutes
                existing.statut         = statut
            else:
                pointage = Pointage(
                    employe_id     = emp_id,
                    date_pointage  = jour,
                    heure_entree   = heure_entree,
                    heure_sortie   = heure_sortie,
                    duree_travail  = duree_heures,
                    retard_minutes = retard_minutes,
                    statut         = statut
                )
                db.add(pointage)

            nb_traites += 1

        db.commit()
        print(f"✅ {nb_traites} pointages traités avec succès!")

        # Stats
        total     = db.query(Pointage).count()
        presents  = db.query(Pointage).filter(Pointage.statut == "Present").count()
        retards   = db.query(Pointage).filter(Pointage.statut == "En retard").count()
        absents   = db.query(Pointage).filter(Pointage.statut == "Absent").count()

        print(f"\n📊 Résumé:")
        print(f"   Total pointages : {total}")
        print(f"   ✅ Présents      : {presents}")
        print(f"   ⚠️  En retard    : {retards}")
        print(f"   ❌ Absents       : {absents}")

    except Exception as e:
        print(f"❌ Erreur: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    process_all_pointages()