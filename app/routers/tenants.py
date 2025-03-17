from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from datetime import datetime

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
@router.get("/{tenant_id}", response_model=schemas.Tenant)
def get_tenant(tenant_id: int, db: Session = Depends(get_db)):
    tenant = service.get_tenant(db, tenant_id=tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

# POST create tenant
@router.post("/", response_model=schemas.Tenant, status_code=status.HTTP_201_CREATED)
def create_tenant(tenant: schemas.TenantCreate, db: Session = Depends(get_db)):
    return service.create_tenant(db, tenant=tenant)

# POST create tenant with images
@router.post("/with-images", response_model=schemas.Tenant, status_code=status.HTTP_201_CREATED)
async def create_tenant_with_images(
    tenant: str = Form(...),
    files: List[UploadFile] = File(None),
    fileFieldPrefix: Optional[str] = Form("file"),
    db: Session = Depends(get_db)
):
    tenant_data = json.loads(tenant)
    tenant_obj = schemas.TenantCreate(**tenant_data)
    
    # Create the tenant first
    new_tenant = service.create_tenant(db, tenant_obj)
    
    # Handle document images if provided
    if files and len(files) > 0:
        for i, file in enumerate(files):
            if fileFieldPrefix == "documentFront" and i == 0:
                doc_url = await service.save_tenant_document(new_tenant.id, file, "front")
                new_tenant = service.update_tenant_document(db, new_tenant.id, doc_url, "front")
            elif fileFieldPrefix == "documentBack" and i == 0:
                doc_url = await service.save_tenant_document(new_tenant.id, file, "back")
                new_tenant = service.update_tenant_document(db, new_tenant.id, doc_url, "back")
    
    return new_tenant

# PUT update tenant
@router.put("/{tenant_id}", response_model=schemas.Tenant)
def update_tenant(
    tenant_id: int,
    tenant: schemas.TenantCreate,
    db: Session = Depends(get_db)
):
    existing_tenant = service.get_tenant(db, tenant_id)
    if existing_tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return service.update_tenant(db, tenant_id, tenant)

# PUT update tenant with images
@router.put("/{tenant_id}/with-images", response_model=schemas.Tenant)
async def update_tenant_with_images(
    tenant_id: int,
    tenant: str = Form(...),
    files: List[UploadFile] = File(None),
    fileFieldPrefix: Optional[str] = Form("file"),
    db: Session = Depends(get_db)
):
    existing_tenant = service.get_tenant(db, tenant_id)
    if existing_tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant_data = json.loads(tenant)
    tenant_obj = schemas.TenantCreate(**tenant_data)
    
    # Update the tenant data
    updated_tenant = service.update_tenant(db, tenant_id, tenant_obj)
    
    # Handle document images if provided
    if files and len(files) > 0:
        for i, file in enumerate(files):
            if fileFieldPrefix == "documentFront" and i == 0:
                doc_url = await service.save_tenant_document(tenant_id, file, "front")
                updated_tenant = service.update_tenant_document(db, tenant_id, doc_url, "front")
            elif fileFieldPrefix == "documentBack" and i == 0:
                doc_url = await service.save_tenant_document(tenant_id, file, "back")
                updated_tenant = service.update_tenant_document(db, tenant_id, doc_url, "back")
    
    return updated_tenant

# DELETE tenant
@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(tenant_id: int, db: Session = Depends(get_db)):
    existing_tenant = service.get_tenant(db, tenant_id)
    if existing_tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    service.delete_tenant(db, tenant_id)
    return {"detail": "Tenant deleted successfully"}

# PATCH update tenant communication preferences
@router.patch("/{tenant_id}/communication-preferences", response_model=schemas.Tenant)
def update_communication_preferences(
    tenant_id: int,
    preferences: schemas.CommunicationPreferences,
    db: Session = Depends(get_db)
):
    existing_tenant = service.get_tenant(db, tenant_id)
    if existing_tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return service.update_tenant_communication_preferences(db, tenant_id, preferences)

# GET tenant's leases
@router.get("/{tenant_id}/leases", response_model=List[schemas.Lease])
def get_tenant_leases(
    tenant_id: int,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    tenant = service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return service.get_tenant_leases(db, tenant_id, is_active)

# GET tenant's active leases
@router.get("/{tenant_id}/active-leases", response_model=List[schemas.Lease])
def get_tenant_active_leases(tenant_id: int, db: Session = Depends(get_db)):
    tenant = service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return service.get_tenant_leases(db, tenant_id, is_active=True)

# GET tenant's invoices
@router.get("/{tenant_id}/invoices", response_model=List[schemas.Invoice])
def get_tenant_invoices(
    tenant_id: int,
    is_paid: Optional[bool] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db)
):
    tenant = service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return service.get_tenant_invoices(db, tenant_id, is_paid, year, month)

# GET tenant's payment history
@router.get("/{tenant_id}/payment-history", response_model=List[schemas.PaymentRecord])
def get_tenant_payment_history(tenant_id: int, db: Session = Depends(get_db)):
    tenant = service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return service.get_tenant_payment_history(db, tenant_id)

# POST upload tenant document
@router.post("/{tenant_id}/documents/{doc_type}", response_model=dict)
async def upload_tenant_document(
    tenant_id: int,
    doc_type: str,
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    tenant = service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if doc_type not in ["front", "back"]:
        raise HTTPException(status_code=400, detail="Document type must be 'front' or 'back'")
    
    doc_url = await service.save_tenant_document(tenant_id, image, doc_type)
    tenant = service.update_tenant_document(db, tenant_id, doc_url, doc_type)
    
    return {"imageUrl": doc_url}

# GET search tenants
@router.get("/search/", response_model=List[schemas.Tenant])
def search_tenants(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db)
):
    return service.search_tenants(db, q)