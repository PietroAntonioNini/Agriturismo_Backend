from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from fastapi import UploadFile, HTTPException
import os
import shutil
from datetime import datetime, timedelta
import uuid
from typing import List, Optional, Dict, Any

from app.models import models
from app.schemas import schemas



# ----- Apartment Services -----

def get_apartments(
    db: Session, 
    skip: int = 0, 
    limit: int = 100, 
    is_available: Optional[bool] = None,
    status: Optional[str] = None,
    floor: Optional[int] = None,
    min_rooms: Optional[int] = None,
    max_price: Optional[float] = None,
    has_balcony: Optional[bool] = None,
    has_parking: Optional[bool] = None,
    is_furnished: Optional[bool] = None
):
    query = db.query(models.Apartment)
    
    if is_available is not None:
        query = query.filter(models.Apartment.is_available == is_available)
    if status:
        query = query.filter(models.Apartment.status == status)
    if floor is not None:
        query = query.filter(models.Apartment.floor == floor)
    if min_rooms is not None:
        query = query.filter(models.Apartment.rooms >= min_rooms)
    if max_price is not None:
        query = query.filter(models.Apartment.monthly_rent <= max_price)
    if has_balcony is not None:
        query = query.filter(models.Apartment.has_balcony == has_balcony)
    if has_parking is not None:
        query = query.filter(models.Apartment.has_parking == has_parking)
    if is_furnished is not None:
        query = query.filter(models.Apartment.is_furnished == is_furnished)
    
    return query.offset(skip).limit(limit).all()

def get_apartment(db: Session, apartment_id: int):
    return db.query(models.Apartment).filter(models.Apartment.id == apartment_id).first()

def create_apartment(db: Session, apartment: schemas.ApartmentCreate):
    db_apartment = models.Apartment(**apartment.dict())
    db.add(db_apartment)
    db.commit()
    db.refresh(db_apartment)
    return db_apartment

def update_apartment(db: Session, apartment_id: int, apartment: schemas.ApartmentCreate):
    db_apartment = db.query(models.Apartment).filter(models.Apartment.id == apartment_id).first()
    if db_apartment:
        for key, value in apartment.dict().items():
            setattr(db_apartment, key, value)
        db_apartment.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_apartment)
    return db_apartment

def delete_apartment(db: Session, apartment_id: int):
    db_apartment = db.query(models.Apartment).filter(models.Apartment.id == apartment_id).first()
    if db_apartment:
        db.delete(db_apartment)
        db.commit()
        return True
    return False

def update_apartment_status(db: Session, apartment_id: int, status: str):
    db_apartment = db.query(models.Apartment).filter(models.Apartment.id == apartment_id).first()
    if db_apartment:
        db_apartment.status = status
        # Update is_available based on status
        db_apartment.is_available = status == "available"
        db_apartment.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_apartment)
    return db_apartment

async def save_apartment_images(apartment_id: int, files: List[UploadFile]):
    """Save multiple apartment images and return the URLs."""
    image_urls = []
    for file in files:
        image_url = await save_apartment_image(apartment_id, file)
        image_urls.append(image_url)
    return image_urls

async def save_apartment_image(apartment_id: int, file: UploadFile):
    """Save a single apartment image and return the URL."""
    # Create directory for apartment images if it doesn't exist
    upload_dir = f"static/apartments/{apartment_id}"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    filename = f"{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
    file_path = f"{upload_dir}/{filename}"
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Return the URL path
    return f"/apartments/{apartment_id}/{filename}"

def update_apartment_images(db: Session, apartment_id: int, image_urls: List[str], append: bool = False):
    """Update apartment images in the database."""
    db_apartment = db.query(models.Apartment).filter(models.Apartment.id == apartment_id).first()
    if db_apartment:
        if append and db_apartment.images:
            # Add new images to existing ones
            current_images = db_apartment.images or []
            db_apartment.images = current_images + image_urls
        else:
            # Replace images
            db_apartment.images = image_urls
        
        db_apartment.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_apartment)
    return db_apartment

def add_apartment_image(db: Session, apartment_id: int, image_url: str):
    """Add a single image to an apartment."""
    db_apartment = db.query(models.Apartment).filter(models.Apartment.id == apartment_id).first()
    if db_apartment:
        if db_apartment.images:
            db_apartment.images.append(image_url)
        else:
            db_apartment.images = [image_url]
        
        db_apartment.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_apartment)
    return db_apartment

def delete_apartment_image(db: Session, apartment_id: int, image_name: str):
    """Delete an image from an apartment."""
    db_apartment = db.query(models.Apartment).filter(models.Apartment.id == apartment_id).first()
    if db_apartment and db_apartment.images:
        image_url = f"/apartments/{apartment_id}/{image_name}"
        if image_url in db_apartment.images:
            db_apartment.images.remove(image_url)
            db_apartment.updated_at = datetime.utcnow()
            db.commit()
            
            # Try to delete the physical file
            try:
                os.remove(f"static{image_url}")
            except:
                pass
            
            return True
    return False

def search_apartments(db: Session, query: str):
    """Search apartments by name or description."""
    search = f"%{query}%"
    return db.query(models.Apartment).filter(
        or_(
            models.Apartment.name.ilike(search),
            models.Apartment.description.ilike(search)
        )
    ).all()

def get_apartment_tenants(db: Session, apartment_id: int):
    """Get all tenants associated with an apartment through active leases."""
    # Query tenants through leases
    tenants = db.query(models.Tenant).join(
        models.Lease, 
        models.Tenant.id == models.Lease.tenant_id
    ).filter(
        models.Lease.apartment_id == apartment_id,
        models.Lease.is_active == True
    ).all()
    
    return tenants

def get_apartment_utilities(
    db: Session, 
    apartment_id: int, 
    type: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None
):
    """Get utility readings for an apartment with optional filters."""
    query = db.query(models.UtilityReading).filter(
        models.UtilityReading.apartment_id == apartment_id
    )
    
    if type:
        query = query.filter(models.UtilityReading.type == type)
    
    if year:
        query = query.filter(
            db.extract('year', models.UtilityReading.reading_date) == year
        )
    
    if month:
        query = query.filter(
            db.extract('month', models.UtilityReading.reading_date) == month
        )
    
    return query.order_by(models.UtilityReading.reading_date.desc()).all()

def get_apartment_maintenance(
    db: Session, 
    apartment_id: int, 
    type: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None
):
    """Get maintenance records for an apartment with optional filters."""
    query = db.query(models.MaintenanceRecord).filter(
        models.MaintenanceRecord.apartment_id == apartment_id
    )
    
    if type:
        query = query.filter(models.MaintenanceRecord.type == type)
    
    if from_date:
        query = query.filter(models.MaintenanceRecord.date >= from_date)
    
    if to_date:
        query = query.filter(models.MaintenanceRecord.date <= to_date)
    
    return query.order_by(models.MaintenanceRecord.date.desc()).all()

def get_apartment_leases(
    db: Session, 
    apartment_id: int, 
    is_active: Optional[bool] = None
):
    """Get leases for an apartment with optional active filter."""
    query = db.query(models.Lease).filter(
        models.Lease.apartment_id == apartment_id
    )
    
    if is_active is not None:
        query = query.filter(models.Lease.is_active == is_active)
    
    return query.order_by(models.Lease.start_date.desc()).all()

def get_apartment_invoices(
    db: Session, 
    apartment_id: int, 
    is_paid: Optional[bool] = None,
    year: Optional[int] = None,
    month: Optional[int] = None
):
    """Get invoices for an apartment with optional filters."""
    query = db.query(models.Invoice).filter(
        models.Invoice.apartment_id == apartment_id
    )
    
    if is_paid is not None:
        query = query.filter(models.Invoice.is_paid == is_paid)
    
    if year:
        query = query.filter(models.Invoice.year == year)
    
    if month:
        query = query.filter(models.Invoice.month == month)
    
    return query.order_by(models.Invoice.issue_date.desc()).all()




# ----- Tenant Services -----

def get_tenants(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Tenant).offset(skip).limit(limit).all()

def get_tenant(db: Session, tenant_id: int):
    return db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()

def create_tenant(db: Session, tenant: schemas.TenantCreate):
    # Convert Pydantic model to dict
    tenant_data = tenant.dict()
    # Handle nested dict for communication_preferences
    tenant_data["communication_preferences"] = tenant_data["communication_preferences"].dict()
    
    db_tenant = models.Tenant(**tenant_data)
    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)
    return db_tenant

def update_tenant(db: Session, tenant_id: int, tenant: schemas.TenantCreate):
    db_tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if db_tenant:
        # Convert tenant data to dict
        tenant_data = tenant.dict()
        # Handle nested dict for communication_preferences
        tenant_data["communication_preferences"] = tenant_data["communication_preferences"].dict()
        
        for key, value in tenant_data.items():
            setattr(db_tenant, key, value)
        
        db_tenant.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_tenant)
    return db_tenant

def delete_tenant(db: Session, tenant_id: int):
    db_tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if db_tenant:
        db.delete(db_tenant)
        db.commit()
        return True
    return False

def update_tenant_communication_preferences(db: Session, tenant_id: int, preferences: schemas.CommunicationPreferences):
    db_tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if db_tenant:
        db_tenant.communication_preferences = preferences.dict()
        db_tenant.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_tenant)
    return db_tenant

async def save_tenant_document(tenant_id: int, file: UploadFile, doc_type: str):
    """Save a tenant document image and return the URL."""
    # Create directory for tenant documents if it doesn't exist
    upload_dir = f"static/tenants/{tenant_id}/documents"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    filename = f"{doc_type}_{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
    file_path = f"{upload_dir}/{filename}"
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Return the URL path
    return f"/tenants/{tenant_id}/documents/{filename}"

def update_tenant_document(db: Session, tenant_id: int, doc_url: str, doc_type: str):
    """Update tenant document URL in the database."""
    db_tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if db_tenant:
        if doc_type == "front":
            db_tenant.document_front_image = doc_url
        elif doc_type == "back":
            db_tenant.document_back_image = doc_url
        
        db_tenant.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_tenant)
    return db_tenant

def get_tenant_leases(db: Session, tenant_id: int, is_active: Optional[bool] = None):
    """Get leases for a tenant with optional active filter."""
    query = db.query(models.Lease).filter(
        models.Lease.tenant_id == tenant_id
    )
    
    if is_active is not None:
        query = query.filter(models.Lease.is_active == is_active)
    
    return query.order_by(models.Lease.start_date.desc()).all()

def get_tenant_invoices(
    db: Session, 
    tenant_id: int, 
    is_paid: Optional[bool] = None,
    year: Optional[int] = None,
    month: Optional[int] = None
):
    """Get invoices for a tenant with optional filters."""
    query = db.query(models.Invoice).filter(
        models.Invoice.tenant_id == tenant_id
    )
    
    if is_paid is not None:
        query = query.filter(models.Invoice.is_paid == is_paid)
    
    if year:
        query = query.filter(models.Invoice.year == year)
    
    if month:
        query = query.filter(models.Invoice.month == month)
    
    return query.order_by(models.Invoice.issue_date.desc()).all()

def get_tenant_payment_history(db: Session, tenant_id: int):
    """Get payment history for a tenant."""
    # This query gets all payment records for invoices associated with this tenant
    return db.query(models.PaymentRecord).join(
        models.Invoice,
        models.PaymentRecord.invoice_id == models.Invoice.id
    ).filter(
        models.Invoice.tenant_id == tenant_id
    ).order_by(models.PaymentRecord.payment_date.desc()).all()

def search_tenants(db: Session, query: str):
    """Search tenants by name, email, or document number."""
    search = f"%{query}%"
    return db.query(models.Tenant).filter(
        or_(
            models.Tenant.first_name.ilike(search),
            models.Tenant.last_name.ilike(search),
            models.Tenant.email.ilike(search),
            models.Tenant.document_number.ilike(search)
        )
    ).all()



    # ----- Lease Services -----

def get_leases(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    is_active: Optional[bool] = None,
    tenant_id: Optional[int] = None,
    apartment_id: Optional[int] = None
):
    """Get leases with optional filters."""
    query = db.query(models.Lease)
    
    if is_active is not None:
        query = query.filter(models.Lease.is_active == is_active)
    
    if tenant_id is not None:
        query = query.filter(models.Lease.tenant_id == tenant_id)
    
    if apartment_id is not None:
        query = query.filter(models.Lease.apartment_id == apartment_id)
    
    return query.offset(skip).limit(limit).all()

def get_lease(db: Session, lease_id: int):
    """Get a specific lease by ID."""
    return db.query(models.Lease).filter(models.Lease.id == lease_id).first()

def create_lease(db: Session, lease: schemas.LeaseCreate):
    """Create a new lease."""
    db_lease = models.Lease(**lease.dict())
    db.add(db_lease)
    db.commit()
    db.refresh(db_lease)
    return db_lease

def update_lease(db: Session, lease_id: int, lease: schemas.LeaseCreate):
    """Update an existing lease."""
    db_lease = db.query(models.Lease).filter(models.Lease.id == lease_id).first()
    if db_lease:
        for key, value in lease.dict().items():
            setattr(db_lease, key, value)
        
        db_lease.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_lease)
    return db_lease

def delete_lease(db: Session, lease_id: int):
    """Delete a lease."""
    db_lease = db.query(models.Lease).filter(models.Lease.id == lease_id).first()
    if db_lease:
        db.delete(db_lease)
        db.commit()
        return True
    return False

def get_expiring_leases(db: Session, days_threshold: int = 30):
    """Get leases that are expiring within the specified number of days."""
    today = datetime.utcnow().date()
    expiry_date = today + timedelta(days=days_threshold)
    
    return db.query(models.Lease).filter(
        models.Lease.is_active == True,
        models.Lease.end_date <= expiry_date,
        models.Lease.end_date >= today
    ).order_by(models.Lease.end_date).all()

async def save_lease_document(lease_id: int, file: UploadFile):
    """Save a lease document file and return the URL."""
    # Create directory for lease documents if it doesn't exist
    upload_dir = f"static/leases/{lease_id}/documents"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    filename = f"{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
    file_path = f"{upload_dir}/{filename}"
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Return the URL path
    return f"/leases/{lease_id}/documents/{filename}"

def create_lease_document(db: Session, document: schemas.LeaseDocumentCreate):
    """Create a new lease document record."""
    db_document = models.LeaseDocument(**document.dict())
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document

def get_lease_document(db: Session, document_id: int):
    """Get a specific lease document by ID."""
    return db.query(models.LeaseDocument).filter(models.LeaseDocument.id == document_id).first()

def get_lease_documents(db: Session, lease_id: int):
    """Get all documents for a specific lease."""
    return db.query(models.LeaseDocument).filter(models.LeaseDocument.lease_id == lease_id).all()

def delete_lease_document(db: Session, document_id: int):
    """Delete a lease document."""
    db_document = db.query(models.LeaseDocument).filter(models.LeaseDocument.id == document_id).first()
    if db_document:
        # Try to delete the physical file
        try:
            file_path = f"static/leases/{db_document.lease_id}/documents/{os.path.basename(db_document.url)}"
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
        
        db.delete(db_document)
        db.commit()
        return True
    return False

def create_lease_payment(db: Session, payment: schemas.LeasePaymentCreate):
    """Create a new lease payment record."""
    db_payment = models.LeasePayment(**payment.dict())
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment

def get_lease_payments(db: Session, lease_id: int):
    """Get all payments for a specific lease."""
    return db.query(models.LeasePayment).filter(models.LeasePayment.lease_id == lease_id).all()

def search_leases(db: Session, query: str):
    """Search leases by associated tenant or apartment."""
    search = f"%{query}%"
    
    # Search by tenant name or apartment name
    return db.query(models.Lease).join(
        models.Tenant, models.Lease.tenant_id == models.Tenant.id
    ).join(
        models.Apartment, models.Lease.apartment_id == models.Apartment.id
    ).filter(
        or_(
            models.Tenant.first_name.ilike(search),
            models.Tenant.last_name.ilike(search),
            models.Apartment.name.ilike(search)
        )
    ).all()





# ----- Utility Reading Services -----

def get_utility_readings(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    apartment_id: Optional[int] = None,
    type: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    is_paid: Optional[bool] = None
):
    """Get utility readings with optional filters."""
    query = db.query(models.UtilityReading)
    
    if apartment_id is not None:
        query = query.filter(models.UtilityReading.apartment_id == apartment_id)
    
    if type is not None:
        query = query.filter(models.UtilityReading.type == type)
    
    if year is not None:
        query = query.filter(db.extract('year', models.UtilityReading.reading_date) == year)
    
    if month is not None:
        query = query.filter(db.extract('month', models.UtilityReading.reading_date) == month)
    
    if is_paid is not None:
        query = query.filter(models.UtilityReading.is_paid == is_paid)
    
    return query.order_by(models.UtilityReading.reading_date.desc()).offset(skip).limit(limit).all()

def get_utility_reading(db: Session, reading_id: int):
    """Get a specific utility reading by ID."""
    return db.query(models.UtilityReading).filter(models.UtilityReading.id == reading_id).first()

def get_last_utility_reading(db: Session, apartment_id: int, type: str):
    """Get the last utility reading for a specific apartment and type."""
    return db.query(models.UtilityReading).filter(
        models.UtilityReading.apartment_id == apartment_id,
        models.UtilityReading.type == type
    ).order_by(models.UtilityReading.reading_date.desc()).first()

def create_utility_reading(db: Session, reading: schemas.UtilityReadingCreate):
    """Create a new utility reading."""
    db_reading = models.UtilityReading(**reading.dict())
    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)
    return db_reading

def update_utility_reading(db: Session, reading_id: int, reading: schemas.UtilityReadingCreate):
    """Update an existing utility reading."""
    db_reading = db.query(models.UtilityReading).filter(models.UtilityReading.id == reading_id).first()
    if db_reading:
        for key, value in reading.dict().items():
            setattr(db_reading, key, value)
        
        db_reading.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_reading)
    return db_reading

def delete_utility_reading(db: Session, reading_id: int):
    """Delete a utility reading."""
    db_reading = db.query(models.UtilityReading).filter(models.UtilityReading.id == reading_id).first()
    if db_reading:
        db.delete(db_reading)
        db.commit()
        return True
    return False

def get_utility_summary(db: Session, apartment_id: int, year: Optional[int] = None):
    """Get utility summary for a specific apartment."""
    # Query utilities
    query = db.query(models.UtilityReading).filter(
        models.UtilityReading.apartment_id == apartment_id
    )
    
    if year:
        query = query.filter(db.extract('year', models.UtilityReading.reading_date) == year)
    
    readings = query.order_by(models.UtilityReading.reading_date).all()
    
    # Group by month and year
    summary_dict = {}
    for reading in readings:
        reading_month = reading.reading_date.month
        reading_year = reading.reading_date.year
        key = f"{reading_year}-{reading_month}"
        
        if key not in summary_dict:
            summary_dict[key] = {
                "apartment_id": apartment_id,
                "month": reading_month,
                "year": reading_year,
                "electricity": {"consumption": 0, "cost": 0},
                "water": {"consumption": 0, "cost": 0},
                "gas": {"consumption": 0, "cost": 0},
                "total_cost": 0
            }
        
        # Add consumption and cost based on type
        if reading.type == "electricity":
            summary_dict[key]["electricity"]["consumption"] += reading.consumption
            summary_dict[key]["electricity"]["cost"] += reading.total_cost
        elif reading.type == "water":
            summary_dict[key]["water"]["consumption"] += reading.consumption
            summary_dict[key]["water"]["cost"] += reading.total_cost
        elif reading.type == "gas":
            summary_dict[key]["gas"]["consumption"] += reading.consumption
            summary_dict[key]["gas"]["cost"] += reading.total_cost
        
        # Update total cost
        summary_dict[key]["total_cost"] += reading.total_cost
    
    # Convert dictionary to list
    summary_list = list(summary_dict.values())
    
    # Sort by year and month
    summary_list.sort(key=lambda x: (x["year"], x["month"]))
    
    return summary_list

def get_yearly_utility_statistics(db: Session, year: int):
    """Get utility statistics for all apartments for a specific year."""
    # Query all readings for the year
    readings = db.query(models.UtilityReading).filter(
        db.extract('year', models.UtilityReading.reading_date) == year
    ).all()
    
    # Group by apartment and month
    stats_dict = {}
    for reading in readings:
        apartment_id = reading.apartment_id
        month = reading.reading_date.month
        key = f"{apartment_id}-{month}"
        
        if key not in stats_dict:
            apartment = db.query(models.Apartment).filter(models.Apartment.id == apartment_id).first()
            apartment_name = apartment.name if apartment else f"Apartment {apartment_id}"
            
            stats_dict[key] = {
                "month": month,
                "year": year,
                "apartment_id": apartment_id,
                "apartment_name": apartment_name,
                "electricity": 0,
                "water": 0,
                "gas": 0
            }
        
        # Add consumption based on type
        if reading.type == "electricity":
            stats_dict[key]["electricity"] += reading.consumption
        elif reading.type == "water":
            stats_dict[key]["water"] += reading.consumption
        elif reading.type == "gas":
            stats_dict[key]["gas"] += reading.consumption
    
    # Convert dictionary to list
    stats_list = list(stats_dict.values())
    
    # Sort by apartment ID and month
    stats_list.sort(key=lambda x: (x["apartment_id"], x["month"]))
    
    return stats_list

def get_apartment_consumption(db: Session, apartment_id: int, year: int):
    """Get utility consumption data for a specific apartment and year."""
    # Query all readings for the apartment and year
    readings = db.query(models.UtilityReading).filter(
        models.UtilityReading.apartment_id == apartment_id,
        db.extract('year', models.UtilityReading.reading_date) == year
    ).all()
    
    # Get the apartment name
    apartment = db.query(models.Apartment).filter(models.Apartment.id == apartment_id).first()
    apartment_name = apartment.name if apartment else f"Apartment {apartment_id}"
    
    # Group by month
    monthly_data = {}
    for month in range(1, 13):
        monthly_data[month] = {
            "month": month,
            "electricity": 0,
            "water": 0,
            "gas": 0
        }
    
    for reading in readings:
        month = reading.reading_date.month
        
        # Add consumption based on type
        if reading.type == "electricity":
            monthly_data[month]["electricity"] += reading.consumption
        elif reading.type == "water":
            monthly_data[month]["water"] += reading.consumption
        elif reading.type == "gas":
            monthly_data[month]["gas"] += reading.consumption
    
    # Create the output structure
    result = {
        "apartment_id": apartment_id,
        "apartment_name": apartment_name,
        "monthly_data": list(monthly_data.values())
    }
    
    return result