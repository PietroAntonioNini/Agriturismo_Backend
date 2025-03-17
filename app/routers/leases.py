from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from datetime import datetime, date

from app.database import get_db
from app.models import models
from app.schemas import schemas
from app.services import service

router = APIRouter(
    prefix="/leases",
    tags=["leases"]
)

# GET all leases with optional filters
@router.get("/", response_model=List[schemas.Lease])
def get_leases(
    skip: int = 0, 
    limit: int = 100,
    is_active: Optional[bool] = None,
    tenant_id: Optional[int] = None,
    apartment_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    return service.get_leases(db, skip, limit, is_active, tenant_id, apartment_id)

# GET lease by ID
@router.get("/{lease_id}", response_model=schemas.Lease)
def get_lease(lease_id: int, db: Session = Depends(get_db)):
    lease = service.get_lease(db, lease_id)
    if lease is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    return lease

# POST create lease
@router.post("/", response_model=schemas.Lease, status_code=status.HTTP_201_CREATED)
def create_lease(lease: schemas.LeaseCreate, db: Session = Depends(get_db)):
    # Verifica che l'appartamento esista e sia disponibile
    apartment = service.get_apartment(db, lease.apartment_id)
    if not apartment:
        raise HTTPException(status_code=404, detail="Apartment not found")
    if not apartment.is_available:
        raise HTTPException(status_code=400, detail="Apartment is not available")
    
    # Verifica che l'inquilino esista
    tenant = service.get_tenant(db, lease.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Crea il contratto
    db_lease = service.create_lease(db, lease)
    
    # Aggiorna lo stato dell'appartamento a "occupied"
    service.update_apartment_status(db, lease.apartment_id, "occupied")
    
    return db_lease

# PUT update lease
@router.put("/{lease_id}", response_model=schemas.Lease)
def update_lease(
    lease_id: int,
    lease: schemas.LeaseCreate,
    db: Session = Depends(get_db)
):
    existing_lease = service.get_lease(db, lease_id)
    if existing_lease is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    
    # Se cambia l'appartamento, verifica che il nuovo sia disponibile
    if lease.apartment_id != existing_lease.apartment_id:
        new_apartment = service.get_apartment(db, lease.apartment_id)
        if not new_apartment:
            raise HTTPException(status_code=404, detail="New apartment not found")
        if not new_apartment.is_available:
            raise HTTPException(status_code=400, detail="New apartment is not available")
        
        # Aggiorna lo stato del vecchio appartamento a "available"
        service.update_apartment_status(db, existing_lease.apartment_id, "available")
        
        # Aggiorna lo stato del nuovo appartamento a "occupied"
        service.update_apartment_status(db, lease.apartment_id, "occupied")
    
    return service.update_lease(db, lease_id, lease)

# DELETE lease
@router.delete("/{lease_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lease(lease_id: int, db: Session = Depends(get_db)):
    existing_lease = service.get_lease(db, lease_id)
    if existing_lease is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    
    # Libera l'appartamento
    service.update_apartment_status(db, existing_lease.apartment_id, "available")
    
    service.delete_lease(db, lease_id)
    return {"detail": "Lease deleted successfully"}

# PATCH terminate lease
@router.patch("/{lease_id}/terminate", response_model=schemas.Lease)
def terminate_lease(
    lease_id: int,
    termination_data: dict,
    db: Session = Depends(get_db)
):
    existing_lease = service.get_lease(db, lease_id)
    if existing_lease is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    
    if not existing_lease.is_active:
        raise HTTPException(status_code=400, detail="Lease is already terminated")
    
    # Verifica che ci sia una data di fine anticipata
    if "end_date" not in termination_data:
        raise HTTPException(status_code=400, detail="End date is required for termination")
    
    try:
        end_date = datetime.strptime(termination_data["end_date"], "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")
    
    # Libera l'appartamento
    service.update_apartment_status(db, existing_lease.apartment_id, "available")
    
    # Aggiorna il contratto
    existing_lease.end_date = end_date
    existing_lease.is_active = False
    existing_lease.notes = termination_data.get("notes", existing_lease.notes)
    existing_lease.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(existing_lease)
    
    return existing_lease

# GET active leases
@router.get("/active/list", response_model=List[schemas.Lease])
def get_active_leases(db: Session = Depends(get_db)):
    return service.get_leases(db, is_active=True)

# GET leases expiring soon
@router.get("/expiring-soon/list", response_model=List[schemas.Lease])
def get_expiring_leases(
    days_threshold: int = Query(30, description="Number of days threshold for expiring leases"),
    db: Session = Depends(get_db)
):
    return service.get_expiring_leases(db, days_threshold)

# POST add document to lease
@router.post("/{lease_id}/documents", response_model=schemas.LeaseDocument)
async def add_lease_document(
    lease_id: int,
    name: str = Form(...),
    type: str = Form(...),
    document: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    lease = service.get_lease(db, lease_id)
    if lease is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    
    document_url = await service.save_lease_document(lease_id, document)
    
    # Crea il documento nel DB
    document_data = {
        "lease_id": lease_id,
        "name": name,
        "type": type,
        "url": document_url,
        "upload_date": datetime.utcnow().date()
    }
    
    return service.create_lease_document(db, schemas.LeaseDocumentCreate(**document_data))

# GET lease documents
@router.get("/{lease_id}/documents", response_model=List[schemas.LeaseDocument])
def get_lease_documents(lease_id: int, db: Session = Depends(get_db)):
    lease = service.get_lease(db, lease_id)
    if lease is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    
    return service.get_lease_documents(db, lease_id)

# DELETE lease document
@router.delete("/{lease_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lease_document(
    lease_id: int,
    document_id: int,
    db: Session = Depends(get_db)
):
    lease = service.get_lease(db, lease_id)
    if lease is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    
    document = service.get_lease_document(db, document_id)
    if document is None or document.lease_id != lease_id:
        raise HTTPException(status_code=404, detail="Document not found")
    
    service.delete_lease_document(db, document_id)
    return {"detail": "Document deleted successfully"}

# POST record lease payment
@router.post("/{lease_id}/payments", response_model=schemas.LeasePayment)
def record_lease_payment(
    lease_id: int,
    payment: schemas.LeasePaymentCreate,
    db: Session = Depends(get_db)
):
    lease = service.get_lease(db, lease_id)
    if lease is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    
    return service.create_lease_payment(db, payment)

# GET lease payments
@router.get("/{lease_id}/payments", response_model=List[schemas.LeasePayment])
def get_lease_payments(lease_id: int, db: Session = Depends(get_db)):
    lease = service.get_lease(db, lease_id)
    if lease is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    
    return service.get_lease_payments(db, lease_id)

# GET search leases
@router.get("/search/", response_model=List[schemas.Lease])
def search_leases(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db)
):
    return service.search_leases(db, q)