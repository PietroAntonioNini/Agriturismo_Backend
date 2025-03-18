from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Query, status, Body
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
    tenants: str = Form(...),
    document0: UploadFile = File(None),
    document1: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    try:
        # Log received data for debugging
        print(f"Received tenants data: {tenants}")
        print(f"Received files: document0={document0 and document0.filename}, document1={document1 and document1.filename}")
        
        # Parse the tenant data
        tenant_data = json.loads(tenants)
        
        # Handle date format conversion for documentExpiryDate
        if "documentExpiryDate" in tenant_data and tenant_data["documentExpiryDate"]:
            # Convert ISO format to date object
            expiry_date_str = tenant_data["documentExpiryDate"]
            if "T" in expiry_date_str:  # If it's in ISO format with time
                expiry_date_str = expiry_date_str.split("T")[0]  # Extract just the date part
            tenant_data["document_expiry_date"] = expiry_date_str
        
        # Handle communication preferences
        if "communicationPreferences" in tenant_data:
            tenant_data["communication_preferences"] = tenant_data.pop("communicationPreferences")
        
        # Convert camelCase to snake_case for all fields
        converted_data = {}
        for key, value in tenant_data.items():
            # Convert camelCase to snake_case
            snake_key = ''.join(['_'+c.lower() if c.isupper() else c for c in key]).lstrip('_')
            converted_data[snake_key] = value
        
        print(f"Converted data: {converted_data}")
        
        # Create tenant object with converted data
        tenant_obj = schemas.TenantCreate(**converted_data)
        
        # Create the tenant first
        new_tenant = service.create_tenant(db, tenant_obj)
        
        # Handle document images if provided
        if document0:
            doc_url = await service.save_tenant_document(new_tenant.id, document0, "front")
            new_tenant = service.update_tenant_document(db, new_tenant.id, doc_url, "front")
        
        if document1:
            doc_url = await service.save_tenant_document(new_tenant.id, document1, "back")
            new_tenant = service.update_tenant_document(db, new_tenant.id, doc_url, "back")
        
        return new_tenant
    
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    
    except ValidationError as e:
        print(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

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
# PUT update tenant with images
@router.put("/{tenant_id}/with-images", response_model=schemas.Tenant)
async def update_tenant_with_images(
    tenant_id: int,
    tenant: str = Form(...),
    documentFrontImage: UploadFile = File(None),
    documentBackImage: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    try:
        # Log received data for debugging
        print(f"Received tenant data: {tenant}")
        print(f"Received files: front={documentFrontImage and documentFrontImage.filename}, back={documentBackImage and documentBackImage.filename}")
        
        existing_tenant = service.get_tenant(db, tenant_id)
        if existing_tenant is None:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        tenant_data = json.loads(tenant)
        
        # Handle date format conversion for documentExpiryDate if needed
        if "documentExpiryDate" in tenant_data and tenant_data["documentExpiryDate"]:
            # Convert ISO format to date object
            expiry_date_str = tenant_data["documentExpiryDate"]
            if "T" in expiry_date_str:  # If it's in ISO format with time
                expiry_date_str = expiry_date_str.split("T")[0]  # Extract just the date part
            tenant_data["documentExpiryDate"] = expiry_date_str
        
        # Create tenant object with data
        tenant_obj = schemas.TenantCreate(**tenant_data)
        
        # Update the tenant data
        updated_tenant = service.update_tenant(db, tenant_id, tenant_obj)
        
        # Handle document images if provided
        if documentFrontImage:
            doc_url = await service.save_tenant_document(tenant_id, documentFrontImage, "front")
            updated_tenant = service.update_tenant_document(db, tenant_id, doc_url, "front")
        
        if documentBackImage:
            doc_url = await service.save_tenant_document(tenant_id, documentBackImage, "back")
            updated_tenant = service.update_tenant_document(db, tenant_id, doc_url, "back")
        
        return updated_tenant
        
    except Exception as e:
        print(f"Error updating tenant with images: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

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