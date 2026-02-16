
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
    id_entita: int = Form(...), # Può essere id_inquilino, id_contratto, etc.
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
        # Leggi il contenuto del file
        content = await file.read()
        
        # Crea un nome file univoco e parlante
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_filename = "".join([c for c in file.filename if c.isalnum() or c in (' ', '.', '_', '-')]).strip()
        
        # Non serve prefisso se ogni tipo ha il suo bucket dedicato
        file_name = f"{id_entita}/{timestamp}_{safe_filename}"
        
        # Mappa il tipo file al bucket
        # R2Manager mappa: 'prospetto', 'contratto', 'documento'
        r2_type = tipo_file
        if 'documento' in tipo_file:
            r2_type = 'documento'
            
        # Upload su Cloudflare R2
        success = r2_manager.upload_file(content, file_name, r2_type)
        
        if success:
            # --- LOGICA DATABASE ---
            try:
                if tipo_file == 'contratto':
                    # Crea record in LeaseDocument
                    lease = db.query(models.Lease).filter(models.Lease.id == id_entita).first()
                    if not lease:
                        logger.warning(f"Lease {id_entita} non trovato per associazione contratto.")
                    else:
                        new_doc = models.LeaseDocument(
                            leaseId=id_entita,
                            name=safe_filename,
                            type='contract',
                            url=file_name,
                            uploadDate=datetime.now(),
                            userId=current_user.id
                        )
                        db.add(new_doc)
                        db.commit()

                elif tipo_file == 'prospetto':
                    # Crea record in LeaseDocument con type='prospectus'
                    lease = db.query(models.Lease).filter(models.Lease.id == id_entita).first()
                    if not lease:
                        logger.warning(f"Lease {id_entita} non trovato per associazione prospetto.")
                    else:
                        # Opzionale: Se c'è già un prospetto eliminare il vecchio?
                        # Per ora aggiungiamo come allegato
                        new_doc = models.LeaseDocument(
                            leaseId=id_entita,
                            name=safe_filename,
                            type='prospectus',
                            url=file_name,
                            uploadDate=datetime.now(),
                            userId=current_user.id
                        )
                        db.add(new_doc)
                        db.commit()
                        
                elif tipo_file in ['documento_fronte', 'documento_retro']:
                    # Aggiorna Tenant
                    tenant = db.query(models.Tenant).filter(models.Tenant.id == id_entita).first()
                    if not tenant:
                        logger.warning(f"Tenant {id_entita} non trovato per associazione documento.")
                    else:
                        if tipo_file == 'documento_fronte':
                            # Se c'è già un file R2, eliminalo
                            if tenant.documentFrontImage and not tenant.documentFrontImage.startswith('/'):
                                r2_manager.delete_file(tenant.documentFrontImage, 'documento_fronte')
                            tenant.documentFrontImage = file_name
                        else:
                            # Se c'è già un file R2, eliminalo
                            if tenant.documentBackImage and not tenant.documentBackImage.startswith('/'):
                                r2_manager.delete_file(tenant.documentBackImage, 'documento_retro')
                            tenant.documentBackImage = file_name
                        db.commit()
                        
            except Exception as db_e:
                logger.error(f"Errore aggiornamento DB: {db_e}")
                # Non blocchiamo l'upload se il DB fallisce, ma logghiamo l'errore
                # O potremmo fare roolback se necessario, ma il file è già su R2.
            
            return {"status": "success", "file_key": file_name, "message": "Caricamento completato e DB aggiornato"}
        else:
            raise HTTPException(status_code=500, detail="Errore durante l'upload su R2")
            
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
         # Non blocchiamo se fallisce R2 (magari non esiste più), ma logghiamo
         logger.warning(f"Eliminazione R2 fallita o file non trovato: {file_key}")

    # 2. Aggiorna il DB
    # Cerca se questo file_key è usato in Tenant
    if 'documento' in tipo_file:
         # Cerca tenant che ha questo URL (esatta corrispondenza o parziale?)
         # file_key è 'documenti_inquilini/ID/...'
         # Nel DB salviamo il file_key intero
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
             db.delete(doc)
             db.commit()
             logger.info(f"Eliminato record LeaseDocument per {file_key}")

    return {"status": "success", "message": "Documento eliminato"}
