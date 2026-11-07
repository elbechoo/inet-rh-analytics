from sqlalchemy import Column, Integer, String, Date, DateTime, Float, Boolean, ForeignKey, Time, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base

# ============================================
# 1. Departement
# ============================================
class Departement(Base):
    __tablename__ = "Departement"

    departement_id    = Column(Integer, primary_key=True, index=True)
    nom_departement   = Column(String(100), nullable=False)
    sous_departement  = Column(String(100))
    date_creation     = Column(DateTime, default=func.now())
    date_modification = Column(DateTime, default=func.now())

    # Relations
    employes = relationship("Employe", back_populates="departement")


# ============================================
# 2. Employe
# ============================================
class Employe(Base):
    __tablename__ = "Employe"

    employe_id        = Column(Integer, primary_key=True, index=True)
    matricule         = Column(String(20), unique=True, nullable=False)
    nom               = Column(String(100), nullable=False)
    prenom            = Column(String(100), nullable=False)
    date_naissance    = Column(Date)
    sexe              = Column(String(10))
    adresse_mail      = Column(String(150), unique=True)
    date_embauche     = Column(Date, nullable=False)
    poste             = Column(String(100))
    type_contrat      = Column(String(50))
    statut            = Column(String(20), default="Actif")
    departement_id    = Column(Integer, ForeignKey("Departement.departement_id"), nullable=False)

    # Reporting line. Self-referential and nullable: the top of the hierarchy
    # reports to nobody, and an employee may legitimately have no manager yet.
    # Without this, a leave request can only be approved by "some HR person" -
    # real approval flows go to the requester's own manager first.
    manager_id        = Column(Integer, ForeignKey("Employe.employe_id"), index=True)

    date_creation     = Column(DateTime, default=func.now())
    date_modification = Column(DateTime, default=func.now())

    # Relations
    departement       = relationship("Departement", back_populates="employes")
    manager           = relationship("Employe", remote_side=[employe_id], backref="subordonnes")
    utilisateur       = relationship("Utilisateur", back_populates="employe", uselist=False)
    pointages         = relationship("Pointage", back_populates="employe")
    pointage_logs     = relationship("PointageLog", back_populates="employe")
    absences          = relationship("Absence", back_populates="employe")
    conges            = relationship("Conge", back_populates="employe", foreign_keys="Conge.employe_id")
    documents         = relationship("Document", back_populates="employe", foreign_keys="Document.employe_id")
    missions          = relationship("Mission", back_populates="employe", foreign_keys="Mission.employe_id")
    formations        = relationship("PresenceFormation", back_populates="employe")
    solde_conge       = relationship("SoldeConge", back_populates="employe", uselist=False)
    alertes           = relationship("AlerteIA", back_populates="employe")


# ============================================
# 3. Utilisateur
# ============================================
class Utilisateur(Base):
    __tablename__ = "Utilisateur"

    user_id           = Column(Integer, primary_key=True, index=True)
    employe_id        = Column(Integer, ForeignKey("Employe.employe_id"), unique=True, nullable=False)
    username          = Column(String(100), unique=True, nullable=False)
    mot_de_passe      = Column(String(255), nullable=False)
    role              = Column(String(20), default="employe")  # employe / rh / admin
    date_creation     = Column(DateTime, default=func.now())
    date_modification = Column(DateTime, default=func.now())

    # Relations
    employe        = relationship("Employe", back_populates="utilisateur")
    admin_employes = relationship("AdminEmploye", back_populates="admin", foreign_keys="AdminEmploye.admin_id")


# ============================================
# 4. Pointage (traité - entrée/sortie calculés)
# ============================================
class Pointage(Base):
    __tablename__ = "Pointage"

    pointage_id       = Column(Integer, primary_key=True, index=True)
    employe_id        = Column(Integer, ForeignKey("Employe.employe_id"), nullable=False)
    date_pointage     = Column(Date, nullable=False)
    heure_entree      = Column(Time)
    heure_debut_pause = Column(Time)   # <- NOUVEAU
    heure_fin_pause   = Column(Time)   # <- NOUVEAU
    heure_sortie      = Column(Time)
    duree_travail     = Column(Float)
    retard_minutes    = Column(Integer, default=0)
    statut            = Column(String(30))
    date_creation     = Column(DateTime, default=func.now())

    employe = relationship("Employe", back_populates="pointages")


# ============================================
# 5. PointageLog (log brut pointeuse)
# ============================================
class PointageLog(Base):
    __tablename__ = "PointageLog"

    log_id               = Column(Integer, primary_key=True, index=True)
    employe_id           = Column(Integer, ForeignKey("Employe.employe_id"), nullable=False)
    timestamp_pointage   = Column(DateTime, nullable=False)
    type_pointage        = Column(String(10))  # ENTREE / SORTIE
    source               = Column(String(50), default="pointeuse")

    # Relations
    employe = relationship("Employe", back_populates="pointage_logs")


# ============================================
# 6. Absence
# ============================================
class Absence(Base):
    __tablename__ = "Absence"

    absence_id    = Column(Integer, primary_key=True, index=True)
    employe_id    = Column(Integer, ForeignKey("Employe.employe_id"), nullable=False)
    date_absence  = Column(Date, nullable=False)
    justifiee     = Column(Boolean, default=False)
    motif         = Column(String(255))
    statut        = Column(String(30), default="Non justifiée")
    date_creation = Column(DateTime, default=func.now())

    # Relations
    employe = relationship("Employe", back_populates="absences")


class TokenRevoke(Base):
    """Sessions ended before their token would have expired.

    A JWT is valid until it expires - the server does not store it, so deleting
    the cookie on logout only stops *this* browser from sending it. A token
    already copied elsewhere keeps working for the rest of its eight hours.

    Rather than store every issued token, this records the moment a user's
    sessions were invalidated. Any token issued before that instant is refused.
    One row per user, updated on logout, so the table stays small and the check
    is a single indexed lookup.
    """
    __tablename__ = "TokenRevoke"

    user_id      = Column(Integer, ForeignKey("Utilisateur.user_id"), primary_key=True)
    revoked_from = Column(DateTime, nullable=False)   # tokens issued before this are dead
    raison       = Column(String(120))
    date_maj     = Column(DateTime, default=func.now(), onupdate=func.now())


class AuditLog(Base):
    """Who did what, to whom, and when.

    HR systems hold decisions that affect pay and employment: a rejected leave
    request, a changed role, a deleted record. When an employee disputes one,
    "the system says so" is not an answer - there has to be a record of which
    account made the change and at what time. Several jurisdictions require it,
    and it is the difference between an HR tool and an HR system of record.

    Append-only by convention: rows are written, never updated or deleted. The
    before/after values are stored as text so any field can be captured without
    a schema change per entity.
    """
    __tablename__ = "AuditLog"

    audit_id      = Column(Integer, primary_key=True, index=True)
    date_action   = Column(DateTime, default=func.now(), nullable=False, index=True)

    # Who. user_id rather than employe_id: the actor is an account, and the
    # account may be deleted later - so the username is denormalised here to
    # keep the trail readable after the fact.
    user_id       = Column(Integer, ForeignKey("Utilisateur.user_id"), index=True)
    username      = Column(String(100))
    role          = Column(String(20))

    # What. e.g. "conge.valider", "employe.delete", "user.role_change"
    action        = Column(String(60), nullable=False, index=True)
    entite        = Column(String(40))          # Conge / Employe / Utilisateur
    entite_id     = Column(Integer, index=True)

    # To whom - the employee affected, when different from the actor.
    cible_employe_id = Column(Integer, index=True)

    ancienne_valeur = Column(String(500))
    nouvelle_valeur = Column(String(500))
    detail          = Column(String(500))
    adresse_ip      = Column(String(45))        # 45 chars covers IPv6


class JourFerie(Base):
    """Public holidays.

    Without this the app treats Aïd like any other Tuesday: leave taken across a
    holiday is deducted from the employee's balance, nobody clocking in that day
    is recorded as absent, and the absenteeism model learns from those phantom
    absences.

    `type_ferie` distinguishes fixed civil dates from the Islamic ones, which
    move roughly 11 days earlier each year and are ultimately set by moon
    sighting - so they are stored per year rather than computed, and HR can
    correct them when the official announcement differs.
    """
    __tablename__ = "JourFerie"

    jour_ferie_id = Column(Integer, primary_key=True, index=True)
    date_ferie    = Column(Date, nullable=False, unique=True, index=True)
    nom           = Column(String(120), nullable=False)
    type_ferie    = Column(String(20), default="civil")   # civil | religieux
    chome         = Column(Boolean, default=True)          # non-working day
    date_creation = Column(DateTime, default=func.now())


# ============================================
# 7. Conge
# ============================================
class Conge(Base):
    __tablename__ = "Conge"

    conge_id        = Column(Integer, primary_key=True, index=True)
    employe_id      = Column(Integer, ForeignKey("Employe.employe_id"), nullable=False)
    type_conge      = Column(String(50))
    date_debut      = Column(Date, nullable=False)
    date_fin        = Column(Date, nullable=False)
    nb_jours        = Column(Integer)
    statut          = Column(String(30), default="En attente")
    commentaire     = Column(String(255))
    date_demande    = Column(DateTime, default=func.now())
    date_validation = Column(DateTime)
    valide_par      = Column(Integer, ForeignKey("Employe.employe_id"))

    # Relations
    employe    = relationship("Employe", back_populates="conges", foreign_keys=[employe_id])
    validateur = relationship("Employe", foreign_keys=[valide_par])


# ============================================
# 8. Document
# ============================================
class Document(Base):
    __tablename__ = "Document"

    document_id     = Column(Integer, primary_key=True, index=True)
    employe_id      = Column(Integer, ForeignKey("Employe.employe_id"), nullable=False)
    type_document   = Column(String(100))
    titre           = Column(String(200))
    date_demande    = Column(DateTime, default=func.now())
    date_validation = Column(DateTime, nullable=True)
    statut          = Column(String(30), default="En attente")
    commentaire     = Column(String(255), nullable=True)
    valide_par      = Column(Integer, ForeignKey("Employe.employe_id"), nullable=True)
    fichier_path    = Column(String(255), nullable=True)

    # Relations
    employe    = relationship("Employe", back_populates="documents", foreign_keys=[employe_id])
    validateur = relationship("Employe", foreign_keys=[valide_par])


# ============================================
# 9. Mission
# ============================================
class Mission(Base):
    __tablename__ = "Mission"

    mission_id        = Column(Integer, primary_key=True, index=True)
    employe_id        = Column(Integer, ForeignKey("Employe.employe_id"), nullable=False)
    lieu              = Column(String(200))
    date_debut        = Column(Date, nullable=False)
    date_fin          = Column(Date, nullable=False)
    role              = Column(String(100))
    type_mission      = Column(String(50))
    statut            = Column(String(30), default="En attente")
    date_declaration  = Column(DateTime, default=func.now())
    valide_par        = Column(Integer, ForeignKey("Employe.employe_id"))

    # Relations
    employe    = relationship("Employe", back_populates="missions", foreign_keys=[employe_id])
    validateur = relationship("Employe", foreign_keys=[valide_par])


# ============================================
# 10. Formation
# ============================================
class Formation(Base):
    __tablename__ = "Formation"

    formation_id   = Column(Integer, primary_key=True, index=True)
    titre          = Column(String(200), nullable=False)
    date_debut     = Column(Date, nullable=False)
    date_fin       = Column(Date, nullable=False)
    organisateur   = Column(String(100))
    type_formation = Column(String(50))
    description    = Column(String(500))
    date_creation  = Column(DateTime, default=func.now())

    # Relations
    presences = relationship("PresenceFormation", back_populates="formation")


# ============================================
# 11. PresenceFormation
# ============================================
class PresenceFormation(Base):
    __tablename__ = "PresenceFormation"

    presence_id  = Column(Integer, primary_key=True, index=True)
    formation_id = Column(Integer, ForeignKey("Formation.formation_id"), nullable=False)
    employe_id   = Column(Integer, ForeignKey("Employe.employe_id"), nullable=False)
    presence     = Column(Boolean, default=False)
    score        = Column(Float)

    # Relations
    formation = relationship("Formation", back_populates="presences")
    employe   = relationship("Employe", back_populates="formations")


# ============================================
# 12. SoldeConge
# ============================================
class SoldeConge(Base):
    __tablename__ = "SoldeConge"

    solde_id      = Column(Integer, primary_key=True, index=True)
    employe_id    = Column(Integer, ForeignKey("Employe.employe_id"), unique=True, nullable=False)
    solde_annuel  = Column(Integer, default=30)
    solde_utilise = Column(Integer, default=0)
    annee         = Column(Integer)

    # Relations
    employe = relationship("Employe", back_populates="solde_conge")


# ============================================
# 13. AlerteIA
# ============================================
class AlerteIA(Base):
    __tablename__ = "AlerteIA"

    alerte_id      = Column(Integer, primary_key=True, index=True)
    employe_id     = Column(Integer, ForeignKey("Employe.employe_id"))
    departement_id = Column(Integer, ForeignKey("Departement.departement_id"))
    type_alerte    = Column(String(100))
    niveau         = Column(String(20))  # Critique, Moyen, Info
    message        = Column(String(500))
    date_alerte    = Column(DateTime, default=func.now())
    est_lue        = Column(Boolean, default=False)

    # Relations
    employe     = relationship("Employe", back_populates="alertes")
    departement = relationship("Departement")


# ============================================
# 14. AdminEmploye (Admin 1 -> N Employe)
# ============================================
class AdminEmploye(Base):
    __tablename__ = "AdminEmploye"

    id         = Column(Integer, primary_key=True, index=True)
    admin_id   = Column(Integer, ForeignKey("Utilisateur.user_id"), nullable=False)
    employe_id = Column(Integer, ForeignKey("Employe.employe_id"), nullable=False)
    date_ajout = Column(DateTime, default=func.now())

    # Relations
    admin   = relationship("Utilisateur", back_populates="admin_employes", foreign_keys=[admin_id])
    employe = relationship("Employe", foreign_keys=[employe_id])


# ============================================
# 15. DW_KPI_Employe (Data Warehouse)
# Schema matches etl/load.py and script.sql.
# employe_id is the PK (not auto-increment - ETL inserts specific IDs).
# ============================================
class DW_KPI_Employe(Base):
    __tablename__ = "DW_KPI_Employe"

    employe_id        = Column(Integer, ForeignKey("Employe.employe_id"), primary_key=True, autoincrement=False)
    nom_complet       = Column(String(200))
    departement       = Column(String(100))
    poste             = Column(String(100))
    anciennete_annees = Column(Integer)
    nb_pointages      = Column(Integer, default=0)
    nb_presents       = Column(Integer, default=0)
    nb_retards        = Column(Integer, default=0)
    nb_absences       = Column(Integer, default=0)
    nb_abs_injust     = Column(Integer, default=0)
    total_heures      = Column(Float, default=0)
    total_retard_min  = Column(Integer, default=0)
    nb_conges         = Column(Integer, default=0)
    jours_conges      = Column(Integer, default=0)
    taux_presence     = Column(Float, default=0)
    taux_absence      = Column(Float, default=0)
    taux_retard       = Column(Float, default=0)
    moy_heures_jour   = Column(Float, default=0)
    date_maj          = Column(DateTime, default=func.now())

    employe = relationship("Employe")


# ============================================
# 16. DW_KPI_Mensuel (Data Warehouse Global)
# Schema matches etl/load.py and script.sql.
# ============================================
class DW_KPI_Mensuel(Base):
    __tablename__ = "DW_KPI_Mensuel"

    id               = Column(Integer, primary_key=True, index=True)
    annee            = Column(Integer)
    mois             = Column(Integer)
    nb_presents      = Column(Integer, default=0)
    nb_absences      = Column(Integer, default=0)
    nb_retards       = Column(Integer, default=0)
    taux_absenteisme = Column(Float, default=0)
    taux_retard      = Column(Float, default=0)
    total_heures     = Column(Float, default=0)
    date_maj         = Column(DateTime, default=func.now())