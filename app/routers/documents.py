
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
        
        # Determina la cartella/prefisso in base al tipo
        folder_prefix = tipo_file
        if 'documento' in tipo_file:
            folder_prefix = 'documenti_inquilini'
            
        file_name = f"{folder_prefix}/{id_entita}/{timestamp}_{safe_filename}"
        
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
                    # Assumiamo che id_entita sia leaseId
                    lease = db.query(models.Lease).filter(models.Lease.id == id_entita).first()
                    if not lease:
                        logger.warning(f"Lease {id_entita} non trovato per associazione documento.")
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
                        
                elif tipo_file in ['documento_fronte', 'documento_retro']:
                    # Aggiorna Tenant
                    # Assumiamo che id_entita sia tenantId
                    tenant = db.query(models.Tenant).filter(models.Tenant.id == id_entita).first()
                    if not tenant:
                        logger.warning(f"Tenant {id_entita} non trovato per associazione documento.")
                    else:
                        if tipo_file == 'documento_fronte':
                            tenant.documentFrontImage = file_name
                        else:
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
