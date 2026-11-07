from fastapi import APIRouter, Depends, HTTPException
from api.deps import get_current_user, require_hr_or_admin, require_self_or_hr
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from config.database import get_db
from services import document_service
from pydantic import BaseModel, Field
from typing import Optional
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter()

# Constrained inputs
class DemandeDocumentSchema(BaseModel):
    employe_id    : int = Field(gt=0)
    type_document : str = Field(min_length=1, max_length=100)

class ValiderDocumentSchema(BaseModel):
    rh_id       : int = Field(gt=0)
    approuve    : bool
    commentaire : Optional[str] = Field(default=None, max_length=1000)

# ── GET tous les documents (RH) ──
@router.get("/")
def get_all_documents(db: Session = Depends(get_db)):
    return document_service.get_all_documents(db)

# ── GET documents en attente (RH) ──
@router.get("/en-attente")
def get_documents_en_attente(db: Session = Depends(get_db)):
    return document_service.get_documents_en_attente(db)

# ── GET documents par employé ──
@router.get("/employe/{employe_id}", dependencies=[Depends(require_self_or_hr)])
def get_documents_employe(employe_id: int, db: Session = Depends(get_db)):
    return document_service.get_documents_employe(db, employe_id)

# ── POST demander un document ──
@router.post("/")
def demander_document(data: DemandeDocumentSchema, db: Session = Depends(get_db)):
    try:
        result = document_service.demander_document(db, data.employe_id, data.type_document)
        return result
    except Exception as e:
        logger.error("POST /documents: %s", e, exc_info=True)
        raise

# ── PUT valider/refuser un document ──
@router.put("/{document_id}/valider", dependencies=[Depends(require_hr_or_admin)])
def valider_document(document_id: int, data: ValiderDocumentSchema, db: Session = Depends(get_db)):
    result = document_service.valider_document(db, document_id, data.rh_id, data.approuve, data.commentaire)
    if not result:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    return result

# ── GET télécharger PDF ──
@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_user),
):
    """Download a document's PDF.

    Keyed by document_id rather than employe_id, so the generic ownership guard
    cannot be used - the owner has to be resolved from the record itself. HR and
    admins may download anything; an employee only their own payslips,
    certificates and contracts.
    """
    from repositories import document_repo
    doc = document_repo.get_document_by_id(db, document_id)
    if not doc or not doc.fichier_path:
        raise HTTPException(status_code=404, detail="PDF non disponible")
    if current["role"] not in ("rh", "admin") and doc.employe_id != current.get("employe_id"):
        # 404 rather than 403: a 403 would confirm the document exists, letting
        # someone enumerate valid IDs.
        raise HTTPException(status_code=404, detail="PDF non disponible")
    if not os.path.exists(doc.fichier_path):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(doc.fichier_path, media_type="application/pdf", filename=f"{doc.type_document}.pdf")
