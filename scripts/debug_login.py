# scripts/debug_login.py
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import SessionLocal
from models.models import Utilisateur, Employe
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = SessionLocal()

print("=" * 50)
print("🔍 TOUS LES UTILISATEURS:")
print("=" * 50)
users = db.query(Utilisateur).all()
for u in users:
    emp = db.query(Employe).filter(Employe.employe_id == u.employe_id).first()
    nom = f"{emp.prenom} {emp.nom}" if emp else "???"
    test = pwd_context.verify("unilog123", u.mot_de_passe)
    print(f"  username: {u.username}")
    print(f"  role:     {u.role}")
    print(f"  employe:  {nom}")
    print(f"  password 'unilog123' OK: {test}")
    print(f"  hash:     {u.mot_de_passe[:30]}...")
    print("-" * 40)

db.close()