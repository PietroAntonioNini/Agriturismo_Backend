
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from app.services.r2_manager import R2Manager
from datetime import datetime
from app.routers.auth import get_current_active_user
import logging

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)
r2_manager = R2Manager()

from sqlalchemy.orm import Session
from app.database import get_db
from app.models import models
from typing import Optional

@router.post("/upload")
async def upload_document(
    id_entita: int = Form(...), # Se 'contratto' -> leaseId, se 'prospetto' -> invoiceId
    tipo_file: str = Form(...), # 'prospetto', 'contratto', 'documento_fronte', 'documento_retro'
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Carica un documento su R2 e aggiorna il database.
    Richiede autenticazione.
    """
    allowed_types = ['prospetto', 'contratto', 'documento_fronte', 'documento_retro']
    if tipo_file not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Tipo file non valido. Ammessi: {', '.join(allowed_types)}")

    try:
        # Recupera leaseId e altre info necessarie in base al tipo
        target_lease_id = None
        target_invoice_id = None
        
        if tipo_file == 'contratto':
            target_lease_id = id_entita
        elif tipo_file == 'prospetto':
            invoice = db.query(models.Invoice).filter(models.Invoice.id == id_entita).first()
            if not invoice:
                raise HTTPException(status_code=404, detail="Fattura non trovata")
            target_lease_id = invoice.leaseId
            target_invoice_id = invoice.id
        elif tipo_file in ['documento_fronte', 'documento_retro']:
            # Per i documenti d'identità usiamo id_entita (tenantId) come sottocartella se necessario, 
            # o lasciamo la logica esistente
            pass

        # Leggi il contenuto del file
        content = await file.read()
        
        # Crea un nome file univoco e parlante
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_filename = "".join([c for c in file.filename if c.isalnum() or c in (' ', '.', '_', '-')]).strip()
        
        # Determina il percorso R2 (file_name)
        # Per contratti e prospetti usiamo SEMPRE il leaseId come prefisso
        if tipo_file in ['contratto', 'prospetto']:
            file_name = f"{target_lease_id}/{timestamp}_{safe_filename}"
        else:
            file_name = f"{id_entita}/{timestamp}_{safe_filename}"
        
        # Mappa il tipo file al bucket
        r2_type = tipo_file
        if 'documento' in tipo_file:
            r2_type = 'documento'
            
        # Upload su Cloudflare R2
        success = r2_manager.upload_file(content, file_name, r2_type)
        
        if success:
            # --- LOGICA DATABASE ---
            try:
                if tipo_file == 'contratto':
                    lease = db.query(models.Lease).filter(models.Lease.id == target_lease_id).first()
                    if lease:
                        lease.hasPdf = True
                        new_doc = models.LeaseDocument(
                            leaseId=target_lease_id,
                            name=safe_filename,
                            type='contract',
                            url=file_name,
                            uploadDate=datetime.now(),
                            userId=current_user.id
                        )
                        db.add(new_doc)
                        db.commit()

                elif tipo_file == 'prospetto':
                    invoice = db.query(models.Invoice).filter(models.Invoice.id == target_invoice_id).first()
                    if invoice:
                        invoice.hasPdf = True
                        new_doc = models.LeaseDocument(
                            leaseId=target_lease_id,
                            invoiceId=target_invoice_id,
                            name=safe_filename,
                            type='prospectus',
                            url=file_name,
                            uploadDate=datetime.now(),
                            userId=current_user.id
                        )
                        db.add(new_doc)
                        db.commit()
                        
                elif tipo_file in ['documento_fronte', 'documento_retro']:
                    tenant = db.query(models.Tenant).filter(models.Tenant.id == id_entita).first()
                    if tenant:
                        if tipo_file == 'documento_fronte':
                            if tenant.documentFrontImage and not tenant.documentFrontImage.startswith('/'):
                                r2_manager.delete_file(tenant.documentFrontImage, 'documento_fronte')
                            tenant.documentFrontImage = file_name
                        else:
                            if tenant.documentBackImage and not tenant.documentBackImage.startswith('/'):
                                r2_manager.delete_file(tenant.documentBackImage, 'documento_retro')
                            tenant.documentBackImage = file_name
                        db.commit()
                        
            except Exception as db_e:
                logger.error(f"Errore aggiornamento DB: {db_e}")
            
            return {"status": "success", "file_key": file_name, "message": "Caricamento completato e DB aggiornato"}
        else:
            raise HTTPException(status_code=500, detail="Errore durante l'upload su R2")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore upload documento: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/url/{file_key:path}")
async def get_document_url(
    file_key: str,
    tipo_file: str,
    current_user = Depends(get_current_active_user)
):
    """
    Ottiene un URL firmato per accedere al documento.
    L'URL scade dopo 1 ora.
    """
    allowed_types = ['prospetto', 'contratto', 'documento_fronte', 'documento_retro']
    if tipo_file not in allowed_types:
        raise HTTPException(status_code=400, detail="Tipo file non valido")

    # Mappa i sottotipi al tipo bucket generico
    r2_type = tipo_file
    if 'documento' in tipo_file:
        r2_type = 'documento'

    url = r2_manager.get_signed_url(file_key, r2_type)
    
    if not url:
        raise HTTPException(status_code=404, detail="Documento non trovato o errore generazione link")
    
    return {"url": url}

@router.delete("/{file_key:path}")
async def delete_document(
    file_key: str,
    tipo_file: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Elimina un documento da R2 e aggiorna il DB se necessario.
    """
    allowed_types = ['prospetto', 'contratto', 'documento_fronte', 'documento_retro', 'documento']
    if tipo_file not in allowed_types:
        raise HTTPException(status_code=400, detail="Tipo file non valido")

    # 1. Elimina da R2
    success = r2_manager.delete_file(file_key, tipo_file)
    if not success:
         logger.warning(f"Eliminazione R2 fallita o file non trovato: {file_key}")

    # 2. Aggiorna il DB
    if 'documento' in tipo_file:
         tenant = db.query(models.Tenant).filter(
             (models.Tenant.documentFrontImage == file_key) | 
             (models.Tenant.documentBackImage == file_key)
         ).first()
         
         if tenant:
             if tenant.documentFrontImage == file_key:
                 tenant.documentFrontImage = None
             if tenant.documentBackImage == file_key:
                 tenant.documentBackImage = None
             db.commit()
             logger.info(f"Rimosso riferimento file {file_key} dal tenant {tenant.id}")

    elif tipo_file in ['contratto', 'prospetto']:
         # Cerca in LeaseDocument
         doc = db.query(models.LeaseDocument).filter(models.LeaseDocument.url == file_key).first()
         if doc:
             # Resetta hasPdf se il documento è di tipo contratto o prospetto
             if doc.type == 'contract':
                 lease = db.query(models.Lease).filter(models.Lease.id == doc.leaseId).first()
                 if lease:
                     lease.hasPdf = False
             elif doc.type == 'prospectus' and doc.invoiceId:
                 invoice = db.query(models.Invoice).filter(models.Invoice.id == doc.invoiceId).first()
                 if invoice:
                     invoice.hasPdf = False
             
             db.delete(doc)
             db.commit()
             logger.info(f"Eliminato record LeaseDocument per {file_key} e aggiornato flag hasPdf")

    return {"status": "success", "message": "Documento eliminato"}
