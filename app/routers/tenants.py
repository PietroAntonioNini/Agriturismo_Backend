import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Query, status, Body
from pydantic import ValidationError
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import time
from datetime import datetime
from fastapi.responses import FileResponse

from app.database import get_db
from app.models import models
from app.schemas import schemas
from app.services import service

router = APIRouter(
    prefix="/tenants",
    tags=["tenants"]
)

# GET all tenants
@router.get("/", response_model=List[schemas.Tenant])
def get_tenants(
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db)
):
    return service.get_tenants(db, skip=skip, limit=limit)

# GET tenant by ID
@router.get("/{tenantId}", response_model=schemas.Tenant)
def get_tenant(tenantId: int, db: Session = Depends(get_db)):
    tenant = service.get_tenant(db, tenantId=tenantId)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

# POST create tenant
@router.post("/", response_model=schemas.Tenant, status_code=status.HTTP_201_CREATED)
def create_tenant(tenant: schemas.TenantCreate, db: Session = Depends(get_db)):
    return service.create_tenant(db, tenant=tenant)

# POST create tenant with images
# POST create tenant with images
@router.post("/with-images", response_model=schemas.Tenant, status_code=status.HTTP_201_CREATED)
async def create_tenant_with_images(
    tenants: str = Form(...),
    document0: UploadFile = File(None),
    document1: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    try:
        # Inizia la transazione manualmente
        tenant_data = json.loads(tenants)
        
        # Gestisci il formato della data
        if "documentExpiryDate" in tenant_data and tenant_data["documentExpiryDate"]:
            expiry_date_str = tenant_data["documentExpiryDate"]
            if "T" in expiry_date_str:
                expiry_date_str = expiry_date_str.split("T")[0]
            tenant_data["documentExpiryDate"] = expiry_date_str
        
        # Crea l'oggetto tenant
        tenant_obj = schemas.TenantCreate(**tenant_data)
        
        # Crea il tenant, ma non fare commit ancora
        new_tenant = service.create_tenant_without_commit(db, tenant_obj)
        
        # Array per tenere traccia dei file salvati
        saved_files = []
        
        try:
            # Gestisci i documenti
            if document0:
                doc_url = await service.save_tenant_document(new_tenant.id, document0, "front")
                saved_files.append(doc_url)
                new_tenant.documentFrontImage = doc_url
            
            if document1:
                doc_url = await service.save_tenant_document(new_tenant.id, document1, "back")
                saved_files.append(doc_url)
                new_tenant.documentBackImage = doc_url
            
            # Completa la transazione
            db.commit()
            
            # Forza un refresh esplicito dell'oggetto tenant per aggiornarne tutti gli attributi
            db.refresh(new_tenant)
            
            # Importante: forzare un flush esplicito per garantire che tutti i dati siano scritti
            db.flush()
            
            # Chiudi e riapri la sessione per evitare problemi di cache
            db.close()
            db = next(get_db())
            
            # Ricaricare il tenant per assicurarsi di avere la versione più aggiornata
            new_tenant = service.get_tenant(db, new_tenant.id)
            
            return new_tenant
            
        except Exception as e:
            # Rollback della transazione in caso di errore
            db.rollback()
            
            # Pulisci i file salvati
            for file_url in saved_files:
                try:
                    clean_url = file_url.split('?')[0]
                    file_path = f"static{clean_url}"
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except:
                    pass
            
            raise e
    
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

# PUT update tenant
@router.put("/{tenantId}", response_model=schemas.Tenant)
def update_tenant(
    tenantId: int,
    tenant: schemas.TenantCreate,
    db: Session = Depends(get_db)
):
    existing_tenant = service.get_tenant(db, tenantId)
    if existing_tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return service.update_tenant(db, tenantId, tenant)

# PUT update tenant with images
@router.put("/{tenantId}/with-images", response_model=schemas.Tenant)
async def update_tenant_with_images(
    tenantId: int,
    tenant: str = Form(...),
    documentFrontImage: UploadFile = File(None),
    documentBackImage: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    try:
        existing_tenant = service.get_tenant(db, tenantId)
        if existing_tenant is None:
            raise HTTPException(status_code=404, detail="Tenant non trovato")
        
        tenant_data = json.loads(tenant)
        
        # Gestione date
        if "documentExpiryDate" in tenant_data and tenant_data["documentExpiryDate"]:
            expiry_date_str = tenant_data["documentExpiryDate"]
            if "T" in expiry_date_str:
                expiry_date_str = expiry_date_str.split("T")[0]
            tenant_data["documentExpiryDate"] = expiry_date_str
        
        # Aggiorna i dati del tenant
        tenant_obj = schemas.TenantCreate(**tenant_data)
        updated_tenant = service.update_tenant(db, tenantId, tenant_obj)
        
        # Gestisci le immagini in parallelo se fornite
        front_image_task = None
        back_image_task = None
        
        if documentFrontImage:
            doc_url = await service.save_tenant_document(tenantId, documentFrontImage, "front")
            updated_tenant = service.update_tenant_document(db, tenantId, doc_url, "front")
        
        if documentBackImage:
            doc_url = await service.save_tenant_document(tenantId, documentBackImage, "back")
            updated_tenant = service.update_tenant_document(db, tenantId, doc_url, "back")
        
        return updated_tenant
        
    except Exception as e:
        print(f"Errore nell'aggiornamento del tenant: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Errore imprevisto: {str(e)}")

# GET download tenant document
@router.get("/{tenantId}/documents/download/{doc_type}", response_class=FileResponse)
async def download_tenant_document(
    tenantId: int,
    doc_type: str,
    db: Session = Depends(get_db)
):
    tenant = service.get_tenant(db, tenantId)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant non trovato")
    
    if doc_type not in ["front", "back"]:
        raise HTTPException(status_code=400, detail="Il tipo di documento deve essere 'front' o 'back'")
    
    # Ottieni il percorso del file
    file_url = None
    if doc_type == "front" and tenant.documentFrontImage:
        file_url = tenant.documentFrontImage.split('?')[0]  # Rimuovi parametri di query
    elif doc_type == "back" and tenant.documentBackImage:
        file_url = tenant.documentBackImage.split('?')[0]  # Rimuovi parametri di query
    
    if not file_url:
        raise HTTPException(status_code=404, detail="Documento non trovato")
    
    file_path = f"static{file_url}"
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File non trovato")
    
    # Restituisci il file con header anti-cache aggressivi
    response = FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type="image/jpeg"  # Potresti determinare dinamicamente il content-type
    )
    
    # Aggiungi header anti-cache aggressivi
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0, post-check=0, pre-check=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Modified"] = str(int(time.time()))
    response.headers["ETag"] = f"\"{uuid.uuid4().hex}\""
    return response

# DELETE tenant
@router.delete("/{tenantId}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(tenantId: int, db: Session = Depends(get_db)):
    existing_tenant = service.get_tenant(db, tenantId)
    if existing_tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    service.delete_tenant(db, tenantId)
    return {"detail": "Tenant deleted successfully"}

# PATCH update tenant communication preferences
@router.patch("/{tenantId}/communication-preferences", response_model=schemas.Tenant)
def update_communication_preferences(
    tenantId: int,
    preferences: schemas.CommunicationPreferences,
    db: Session = Depends(get_db)
):
    existing_tenant = service.get_tenant(db, tenantId)
    if existing_tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return service.update_tenant_communication_preferences(db, tenantId, preferences)

# GET tenant's leases
@router.get("/{tenantId}/leases", response_model=List[schemas.Lease])
def get_tenant_leases(
    tenantId: int,
    isActive: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    tenant = service.get_tenant(db, tenantId)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return service.get_tenant_leases(db, tenantId, isActive)

# GET tenant's active leases
@router.get("/{tenantId}/active-leases", response_model=List[schemas.Lease])
def get_tenant_active_leases(tenantId: int, db: Session = Depends(get_db)):
    tenant = service.get_tenant(db, tenantId)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return service.get_tenant_leases(db, tenantId, isActive=True)

# GET tenant's invoices
@router.get("/{tenantId}/invoices", response_model=List[schemas.Invoice])
def get_tenant_invoices(
    tenantId: int,
    isPaid: Optional[bool] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db)
):
    tenant = service.get_tenant(db, tenantId)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return service.get_tenant_invoices(db, tenantId, isPaid, year, month)

# GET tenant's payment history
@router.get("/{tenantId}/payment-history", response_model=List[schemas.PaymentRecord])
def get_tenant_payment_history(tenantId: int, db: Session = Depends(get_db)):
    tenant = service.get_tenant(db, tenantId)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return service.get_tenant_payment_history(db, tenantId)

# POST upload tenant document
@router.post("/{tenantId}/documents/{doc_type}", response_model=schemas.DocumentResponse)
async def upload_tenant_document(
    tenantId: int,
    doc_type: str,
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    tenant = service.get_tenant(db, tenantId)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant non trovato")
    
    if doc_type not in ["front", "back"]:
        raise HTTPException(status_code=400, detail="Il tipo di documento deve essere 'front' o 'back'")
    
    # Salva la nuova immagine in modo asincrono
    doc_url = await service.save_tenant_document(tenantId, image, doc_type)
    
    # Aggiorna il database
    updated_tenant = service.update_tenant_document(db, tenantId, doc_url, doc_type)
    
    # Verifica che l'URL sia stato effettivamente aggiornato
    verified_url = ""
    if doc_type == "front":
        verified_url = updated_tenant.documentFrontImage
    elif doc_type == "back":
        verified_url = updated_tenant.documentBackImage
    
    return {
        "imageUrl": verified_url,
        "success": True,
        "timestamp": int(time.time())
    }

# GET search tenants
@router.get("/search/", response_model=List[schemas.Tenant])
def search_tenants(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db)
):
    return service.search_tenants(db, q)

# DELETE tenant document
@router.delete("/{tenantId}/documents/{doc_type}", response_model=schemas.DocumentResponse)
async def delete_tenant_document(
    tenantId: int,
    doc_type: str,
    db: Session = Depends(get_db)
):
    if doc_type not in ["front", "back"]:
        raise HTTPException(status_code=400, detail="Il tipo di documento deve essere 'front' o 'back'")
    
    result = await service.delete_tenant_document(db, tenantId, doc_type)
    return {
        "success": True,
        "detail": "Documento eliminato con successo",
        "timestamp": int(time.time())
    }