from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
import logging

from app.database import get_db
from app.models import models
from app.schemas import schemas
from app.services import service
from app.core.auth import get_current_active_user

# Configurazione logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/invoices",
    tags=["invoices"]
)

# GET all invoices with filters
@router.get("/", response_model=List[schemas.Invoice])
def get_invoices(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = Query(None, description="Filter by status: paid, unpaid, overdue"),
    tenant_id: Optional[int] = Query(None, alias="tenantId"),
    apartment_id: Optional[int] = Query(None, alias="apartmentId"),
    lease_id: Optional[int] = Query(None, alias="leaseId"),
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2020),
    start_date: Optional[date] = Query(None, alias="startDate"),
    end_date: Optional[date] = Query(None, alias="endDate"),
    search: Optional[str] = Query(None, description="Search in invoice number"),
    sort_by: Optional[str] = Query("issueDate", description="Sort by: issueDate, dueDate, total, invoiceNumber"),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc, desc"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get all invoices with optional filters"""
    return service.get_invoices(
        db, skip, limit, status, tenant_id, apartment_id, lease_id,
        month, year, start_date, end_date, search, sort_by, sort_order
    )

# GET single invoice
@router.get("/{invoice_id}", response_model=schemas.Invoice)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get a single invoice by ID"""
    invoice = service.get_invoice(db, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

# POST create invoice
@router.post("/", response_model=schemas.Invoice, status_code=status.HTTP_201_CREATED)
def create_invoice(
    invoice: schemas.InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Create a new invoice"""
    return service.create_invoice(db, invoice)

# PUT update invoice
@router.put("/{invoice_id}", response_model=schemas.Invoice)
def update_invoice(
    invoice_id: int,
    invoice: schemas.InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Update an existing invoice"""
    updated_invoice = service.update_invoice(db, invoice_id, invoice)
    if updated_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return updated_invoice

# DELETE invoice
@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete an invoice"""
    success = service.delete_invoice(db, invoice_id)
    if not success:
        raise HTTPException(status_code=404, detail="Invoice not found")

# POST mark invoice as paid
@router.post("/{invoice_id}/mark-as-paid", response_model=schemas.Invoice)
def mark_invoice_as_paid(
    invoice_id: int,
    payment_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Mark an invoice as paid"""
    invoice = service.mark_invoice_as_paid(db, invoice_id, payment_data)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

# POST add payment record
@router.post("/{invoice_id}/payment-records", response_model=schemas.PaymentRecord)
def add_payment_record(
    invoice_id: int,
    payment_record: schemas.PaymentRecordCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Add a payment record to an invoice"""
    record = service.add_payment_record(db, invoice_id, payment_record)
    if record is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return record

# GET payment records for invoice
@router.get("/{invoice_id}/payment-records", response_model=List[schemas.PaymentRecord])
def get_invoice_payment_records(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get all payment records for an invoice"""
    records = service.get_invoice_payment_records(db, invoice_id)
    if records is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return records

# POST send reminder
@router.post("/{invoice_id}/send-reminder")
def send_invoice_reminder(
    invoice_id: int,
    reminder_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Send a reminder for an invoice"""
    result = service.send_invoice_reminder(db, invoice_id, reminder_data)
    if result is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return result

# GET overdue invoices
@router.get("/overdue", response_model=List[schemas.Invoice])
def get_overdue_invoices(
    days_overdue: Optional[int] = Query(7, description="Minimum days overdue"),
    include_tenant_info: Optional[bool] = Query(True, alias="includeTenantInfo"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get overdue invoices"""
    return service.get_overdue_invoices(db, days_overdue, include_tenant_info)

# POST generate monthly invoices
@router.post("/generate-monthly")
def generate_monthly_invoices(
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Generate monthly invoices for all active leases"""
    return service.generate_monthly_invoices(db, data)

# POST generate invoice from lease
@router.post("/generate-from-lease")
def generate_invoice_from_lease(
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Generate an invoice from a specific lease"""
    return service.generate_invoice_from_lease(db, data)

# GET invoice statistics
@router.get("/statistics")
def get_invoice_statistics(
    period: Optional[str] = Query("this_month", description="Period: this_month, last_month, this_year, all"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get invoice statistics and KPI"""
    return service.get_invoice_statistics(db, period)

# GET invoice PDF
@router.get("/{invoice_id}/pdf")
def get_invoice_pdf(
    invoice_id: int,
    include_logo: Optional[bool] = Query(True, alias="includeLogo"),
    include_qr_code: Optional[bool] = Query(True, alias="includeQrCode"),
    include_payment_instructions: Optional[bool] = Query(True, alias="includePaymentInstructions"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Generate PDF for an invoice"""
    pdf_data = service.generate_invoice_pdf(
        db, invoice_id, include_logo, include_qr_code, include_payment_instructions
    )
    if pdf_data is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return pdf_data

# POST send bulk reminders
@router.post("/send-bulk-reminders")
def send_bulk_reminders(
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Send reminders for multiple invoices"""
    return service.send_bulk_reminders(db, data) 