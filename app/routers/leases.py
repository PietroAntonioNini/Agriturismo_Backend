from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from datetime import datetime, date

from app.database import get_db
from app.models import models
from app.schemas import schemas
from app.services import service

from app.core.auth import get_current_active_user

router = APIRouter(
    prefix="/leases",
    tags=["leases"]
)

# GET all leases with optional filters
@router.get("/", response_model=List[schemas.Lease])
def get_leases(
    skip: int = 0, 
    limit: int = 100,
    status: Optional[str] = None,
    tenantId: Optional[int] = None,
    apartmentId: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    return service.get_leases(db, skip, limit, status, tenantId, apartmentId, current_user.id)

# GET lease by ID
@router.get("/{leaseId}", response_model=schemas.Lease)
def get_lease(leaseId: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    lease = service.get_lease(db, leaseId, current_user.id)
    if lease is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    return lease

# POST create lease
@router.post("/", response_model=schemas.Lease, status_code=status.HTTP_201_CREATED)
def create_lease(
    lease: schemas.LeaseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Verifica che l'appartamento esista e sia disponibile
    apartment = service.get_apartment(db, lease.apartmentId, current_user.id)
    if not apartment:
        raise HTTPException(status_code=404, detail="Apartment not found")
    if apartment.status != "available":
        raise HTTPException(status_code=400, detail="Apartment is not available")
    
    # Verifica che l'inquilino esista
    tenant = service.get_tenant(db, lease.tenantId)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Crea il contratto
    db_lease = service.create_lease(db, lease, user_id=current_user.id)
    
    # Aggiorna lo stato dell'appartamento a "occupied"
    service.update_apartment_status(db, lease.apartmentId, "occupied")
    
    return db_lease

# PUT update lease
@router.put("/{leaseId}", response_model=schemas.Lease)
def update_lease(
    leaseId: int,
    lease: schemas.LeaseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    existing_lease = service.get_lease(db, leaseId, current_user.id)
    if existing_lease is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    
    # Se cambia l'appartamento, verifica che il nuovo sia disponibile
    if lease.apartmentId != existing_lease.apartmentId:
        new_apartment = service.get_apartment(db, lease.apartmentId, current_user.id)
        if not new_apartment:
            raise HTTPException(status_code=404, detail="New apartment not found")
        if new_apartment.status != "available":
            raise HTTPException(status_code=400, detail="New apartment is not available")
        
        # Aggiorna lo stato del vecchio appartamento a "available"
        service.update_apartment_status(db, existing_lease.apartmentId, "available")
        
        # Aggiorna lo stato del nuovo appartamento a "occupied"
        service.update_apartment_status(db, lease.apartmentId, "occupied")
    
    return service.update_lease(db, leaseId, lease)

# DELETE lease
@router.delete("/{leaseId}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lease(leaseId: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    existing_lease = service.get_lease(db, leaseId, current_user.id)
    if existing_lease is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    
    # Libera l'appartamento
    service.update_apartment_status(db, existing_lease.apartmentId, "available")
    
    service.delete_lease(db, leaseId)
    return {"detail": "Lease deleted successfully"}

# PATCH terminate lease
@router.patch("/{leaseId}/terminate", response_model=schemas.Lease)
def terminate_lease(
    leaseId: int,
    termination_data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    existing_lease = service.get_lease(db, leaseId, current_user.id)
    if existing_lease is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    
    if not existing_lease.isActive:
        raise HTTPException(status_code=400, detail="Lease is already terminated")
    
    # Verifica che ci sia una data di fine anticipata
    if "endDate" not in termination_data:
        raise HTTPException(status_code=400, detail="End date is required for termination")
    
    try:
        endDate = datetime.strptime(termination_data["endDate"], "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")
    
    # Libera l'appartamento
    service.update_apartment_status(db, existing_lease.apartmentId, "available")
    
    # Aggiorna il contratto
    existing_lease.endDate = endDate
    existing_lease.notes = termination_data.get("notes", existing_lease.notes)
    existing_lease.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(existing_lease)
    
    return existing_lease

# GET leases expiring soon
@router.get("/expiring-soon/list", response_model=List[schemas.Lease])
def get_expiring_leases(
    days_threshold: int = Query(30, description="Number of days threshold for expiring leases"),
    db: Session = Depends(get_db)
):
    return service.get_expiring_leases(db, days_threshold)

# POST add document to lease
@router.post("/{leaseId}/documents", response_model=schemas.LeaseDocument)
async def add_lease_document(
    leaseId: int,
    name: str = Form(...),
    type: str = Form(...),
    document: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    lease = service.get_lease(db, leaseId)
    if lease is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    
    document_url = await service.save_lease_document(leaseId, document)
    
    # Crea il documento nel DB
    document_data = {
        "leaseId": leaseId,
        "name": name,
        "type": type,
        "url": document_url,
        "uploadDate": datetime.utcnow().date()
    }
    
    return service.create_lease_document(db, schemas.LeaseDocumentCreate(**document_data))

# GET lease documents
@router.get("/{leaseId}/documents", response_model=List[schemas.LeaseDocument])
def get_lease_documents(leaseId: int, db: Session = Depends(get_db)):
    lease = service.get_lease(db, leaseId)
    if lease is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    
    return service.get_lease_documents(db, leaseId)

# DELETE lease document
@router.delete("/{leaseId}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lease_document(
    leaseId: int,
    document_id: int,
    db: Session = Depends(get_db)
):
    lease = service.get_lease(db, leaseId)
    if lease is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    
    document = service.get_lease_document(db, document_id)
    if document is None or document.leaseId != leaseId:
        raise HTTPException(status_code=404, detail="Document not found")
    
    service.delete_lease_document(db, document_id)
    return {"detail": "Document deleted successfully"}

# POST record lease payment
@router.post("/{leaseId}/payments", response_model=schemas.LeasePayment)
def record_lease_payment(
    leaseId: int,
    payment: schemas.LeasePaymentCreate,
    db: Session = Depends(get_db)
):
    lease = service.get_lease(db, leaseId)
    if lease is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    
    return service.create_lease_payment(db, payment)

# GET lease payments
@router.get("/{leaseId}/payments", response_model=List[schemas.LeasePayment])
def get_lease_payments(leaseId: int, db: Session = Depends(get_db)):
    lease = service.get_lease(db, leaseId)
    if lease is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    
    return service.get_lease_payments(db, leaseId)

# GET search leases
@router.get("/search/", response_model=List[schemas.Lease])
def search_leases(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db)
):
    return service.search_leases(db, q)

# GET lease's invoices
@router.get("/{leaseId}/invoices", response_model=List[schemas.Invoice])
def get_lease_invoices(
    leaseId: int,
    isPaid: Optional[bool] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db)
):
    lease = service.get_lease(db, leaseId)
    if lease is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    return service.get_lease_invoices(db, leaseId, isPaid, year, month)