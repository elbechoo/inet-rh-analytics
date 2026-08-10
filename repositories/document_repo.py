from sqlalchemy.orm import Session
from models.models import Document
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def get_documents_by_employe(db: Session, employe_id: int):
    return db.query(Document).filter(Document.employe_id == employe_id).order_by(Document.date_demande.desc()).all()

def get_all_documents(db: Session):
    return db.query(Document).order_by(Document.date_demande.desc()).all()

def get_documents_en_attente(db: Session):
    return db.query(Document).filter(Document.statut == "En attente").order_by(Document.date_demande.desc()).all()

def create_document(db: Session, employe_id: int, type_document: str, titre: str):
    try:
        doc = Document(
            employe_id    = employe_id,
            type_document = type_document,
            titre         = titre,
            statut        = "En attente",
            date_demande  = datetime.now()
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc
    except Exception as e:
        logger.error("create_document: %s", e)
        db.rollback()
        raise

def valider_document(db: Session, document_id: int, rh_id: int, approuve: bool, commentaire: str = None, fichier_path: str = None):
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        return None
    doc.statut          = "Approuvé" if approuve else "Refusé"
    doc.valide_par      = rh_id
    doc.date_validation = datetime.now()
    doc.commentaire     = commentaire
    doc.fichier_path    = fichier_path
    db.commit()
    db.refresh(doc)
    return doc

def get_document_by_id(db: Session, document_id: int):
    return db.query(Document).filter(Document.document_id == document_id).first()