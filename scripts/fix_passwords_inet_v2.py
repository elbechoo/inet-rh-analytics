"""
Script Python - Reset passwords iNET
Utilise passlib (même lib que employe_service.py)
Exécuter: python fix_passwords_inet_v2.py
"""
import sys
import os

# Ajouter le path du projet
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from passlib.context import CryptContext
import pyodbc

# ============================================
# Même config que employe_service.py
# ============================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ============================================
# Config DB
# ============================================
conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=GestionRH_Intelligente;"
    "Trusted_Connection=yes;"
)
cursor = conn.cursor()

# ============================================
# Test verify avant de commencer
# ============================================
test_hash = hash_password("inet123")
print(f"✅ Test hash: {test_hash[:30]}...")
print(f"✅ Test verify: {verify_password('inet123', test_hash)}")
print()

# ============================================
# Reset comptes privilégiés
# ============================================
accounts = [
    ("riadh.abbes",       "inet123", "Admin"),
    ("nadia.khaldi",      "inet123", "RH"),
    ("ahmad.amri",        "inet123", "RH"),
    ("mohamed.ali.amri",  "inet123", "RH"),
    ("abdelkarim.douzi",  "inet123", "RH"),
]

print("🔄 Reset comptes privilégiés...\n")
for username, password, role in accounts:
    hashed = hash_password(password)
    cursor.execute(
        "UPDATE Utilisateur SET mot_de_passe = ? WHERE username = ?",
        (hashed, username)
    )
    rows = cursor.rowcount
    status = "✅ OK" if rows > 0 else "❌ NOT FOUND"
    print(f"  {status} - [{role}] {username}")

# ============================================
# Reset TOUS les employés
# ============================================
print("\n🔄 Reset tous les employés (inet123)...")
hashed_default = hash_password("inet123")
cursor.execute(
    "UPDATE Utilisateur SET mot_de_passe = ? WHERE role = 'employe'",
    (hashed_default,)
)
print(f"  ✅ {cursor.rowcount} employés mis à jour")

conn.commit()

# ============================================
# Vérification finale - test login
# ============================================
print("\n🔍 Vérification finale...\n")
test_accounts = ["riadh.abbes", "nadia.khaldi", "ahmad.amri"]
for username in test_accounts:
    cursor.execute(
        "SELECT mot_de_passe, role FROM Utilisateur WHERE username = ?",
        (username,)
    )
    row = cursor.fetchone()
    if row:
        hashed_db, role = row
        ok = verify_password("inet123", hashed_db)
        print(f"  {'✅' if ok else '❌'} {username} [{role}] - login {'OK' if ok else 'FAIL'}")
    else:
        print(f"  ❌ {username} - NOT FOUND in DB")

cursor.close()
conn.close()

print("\n✅ Terminé!")
print("\n📋 Credentials:")
print("┌─────────────────────┬──────────┬─────────┐")
print("│ Username            │ Password │ Rôle    │")
print("├─────────────────────┼──────────┼─────────┤")
print("│ riadh.abbes         │ inet123  │ Admin   │")
print("│ nadia.khaldi        │ inet123  │ RH      │")
print("│ ahmad.amri          │ inet123  │ RH      │")
print("│ prenom.nom          │ inet123  │ Employé │")
print("└─────────────────────┴──────────┴─────────┘")