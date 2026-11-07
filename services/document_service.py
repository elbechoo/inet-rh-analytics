from sqlalchemy.orm import Session
from models.models import Document, Employe
from repositories import document_repo
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

def doc_to_dict(doc) -> dict:
    return {
        "document_id"    : doc.document_id,
        "employe_id"     : doc.employe_id,
        "type_document"  : doc.type_document,
        "titre"          : doc.titre,
        "statut"         : doc.statut,
        "date_demande"   : str(doc.date_demande) if doc.date_demande else None,
        "date_validation": str(doc.date_validation) if doc.date_validation else None,
        "commentaire"    : doc.commentaire,
        "valide_par"     : doc.valide_par,
        "fichier_path"   : doc.fichier_path,
    }

def get_documents_employe(db: Session, employe_id: int):
    docs = document_repo.get_documents_by_employe(db, employe_id)
    return [doc_to_dict(d) for d in docs]

def get_all_documents(db: Session):
    docs = document_repo.get_all_documents(db)
    return [doc_to_dict(d) for d in docs]

def get_documents_en_attente(db: Session):
    docs = document_repo.get_documents_en_attente(db)
    return [doc_to_dict(d) for d in docs]

def demander_document(db: Session, employe_id: int, type_document: str):
    titres = {
        "Attestation de travail" : "Attestation de travail",
        "Fiche de paie"          : "Fiche de paie",
        "Attestation de salaire" : "Attestation de salaire",
    }
    titre = titres.get(type_document, type_document)
    doc = document_repo.create_document(db, employe_id, type_document, titre)
    return doc_to_dict(doc)

def valider_document(db: Session, document_id: int, rh_id: int, approuve: bool, commentaire: str = None):
    fichier_path = None
    if approuve:
        fichier_path = generer_pdf(db, document_id)
    doc = document_repo.valider_document(db, document_id, rh_id, approuve, commentaire, fichier_path)
    return doc_to_dict(doc) if doc else None

def generer_pdf(db: Session, document_id: int):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        doc = document_repo.get_document_by_id(db, document_id)
        if not doc:
            return None

        employe = db.query(Employe).filter(Employe.employe_id == doc.employe_id).first()
        if not employe:
            return None

        os.makedirs("documents_pdf", exist_ok=True)
        filename = f"documents_pdf/doc_{document_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"

        c = canvas.Canvas(filename, pagesize=A4)
        width, height = A4
        from reportlab.lib.units import cm

        # Header
        c.setFillColorRGB(0, 0.157, 0.306)
        c.rect(0, height - 80, width, 80, fill=True, stroke=False)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(2*cm, height - 50, "iNET")
        c.setFont("Helvetica", 10)
        c.drawString(2*cm, height - 65, "Informatique.Net - Gestion RH")

        # Title
        c.setFillColorRGB(0, 0.157, 0.306)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width/2, height - 130, doc.type_document.upper())

        # Line
        c.setStrokeColorRGB(0, 0.69, 0.918)
        c.setLineWidth(2)
        c.line(2*cm, height - 145, width - 2*cm, height - 145)

        # Content
        c.setFillColorRGB(0.18, 0.18, 0.18)
        c.setFont("Helvetica", 11)
        y = height - 190

        lines = [
            "Nous soussignés, la Direction des Ressources Humaines de la société iNET,",
            "certifions que :",
            "",
            f"   Nom et Prénom   :  {employe.prenom} {employe.nom}",
            f"   Matricule        :  {employe.matricule}",
            f"   Poste            :  {employe.poste or '-'}",
            f"   Type de contrat  :  {employe.type_contrat or '-'}",
            f"   Date d'embauche  :  {employe.date_embauche or '-'}",
            "",
            "est bien employé(e) au sein de notre société.",
            "",
            "Cette attestation est délivrée à l'intéressé(e) pour servir et valoir",
            "ce que de droit.",
        ]

        for line in lines:
            c.drawString(2*cm, y, line)
            y -= 20

        y -= 20
        c.setFont("Helvetica", 10)
        c.drawString(2*cm, y, f"Fait à Tunis, le {datetime.now().strftime('%d/%m/%Y')}")
        y -= 40
        c.drawRightString(width - 2*cm, y, "Signature & Cachet")
        y -= 15
        c.drawRightString(width - 2*cm, y, "Direction RH - iNET")

        # Footer
        c.setFillColorRGB(0, 0.157, 0.306)
        c.rect(0, 0, width, 30, fill=True, stroke=False)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica", 8)
        c.drawCentredString(width/2, 10, "iNET - Informatique.Net © 2025 | document généré automatiquement")

        c.save()
        return filename

    except Exception as e:
        logger.error("PDF generation error: %s", e)
        return None