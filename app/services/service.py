from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from fastapi import UploadFile, HTTPException
import os
import shutil
from datetime import datetime, timedelta, date
import uuid
from typing import List, Optional, Dict, Any
import time
import imghdr  # Per la validazione del tipo di immagine
import aiofiles  # Per operazioni asincrone sui file

from app.models import models
from app.schemas import schemas
from app.services.billing_defaults_service import get_defaults



# ----- Apartment Services -----

def get_apartments(
    db: Session, 
    skip: int = 0,  
    limit: int = 100, 
    status: Optional[str] = None,
    floor: Optional[int] = None,
    minRooms: Optional[int] = None,
    maxPrice: Optional[float] = None,
    hasBalcony: Optional[bool] = None,
    hasParking: Optional[bool] = None,
    isFurnished: Optional[bool] = None,
    user_id: Optional[int] = None
):
    query = db.query(models.Apartment)
    # Soft delete filter
    if hasattr(models.Apartment, "deletedAt"):
        query = query.filter(models.Apartment.deletedAt.is_(None))
    # Multi-tenancy filter
    if user_id is not None:
        query = query.filter(models.Apartment.userId == user_id)
    
    # Filter directly by status
    if status:
        query = query.filter(models.Apartment.status == status)
    if floor is not None:
        query = query.filter(models.Apartment.floor == floor)
    if minRooms is not None:
        query = query.filter(models.Apartment.rooms >= minRooms)
    if maxPrice is not None:
        query = query.filter(models.Apartment.monthlyRent <= maxPrice)
    if hasBalcony is not None:
        query = query.filter(models.Apartment.hasBalcony == hasBalcony)
    if hasParking is not None:
        query = query.filter(models.Apartment.hasParking == hasParking)
    if isFurnished is not None:
        query = query.filter(models.Apartment.isFurnished == isFurnished)
    
    return query.offset(skip).limit(limit).all()

def get_apartment(db: Session, apartmentId: int, user_id: Optional[int] = None):
    query = db.query(models.Apartment).filter(models.Apartment.id == apartmentId)
    if hasattr(models.Apartment, "deletedAt"):
        query = query.filter(models.Apartment.deletedAt.is_(None))
    if user_id is not None:
        query = query.filter(models.Apartment.userId == user_id)
    return query.first()

def create_apartment(db: Session, apartment: schemas.ApartmentCreate, user_id: Optional[int] = None):
    data = apartment.dict()
    if user_id is not None:
        data["userId"] = user_id
    db_apartment = models.Apartment(**data)
    db.add(db_apartment)
    db.commit()
    db.refresh(db_apartment)
    return db_apartment

def update_apartment(db: Session, apartmentId: int, apartment: schemas.ApartmentCreate):
    db_apartment = db.query(models.Apartment).filter(models.Apartment.id == apartmentId).first()
    if db_apartment:
        for key, value in apartment.dict().items():
            setattr(db_apartment, key, value)
        setattr(db_apartment, "updatedAt", datetime.utcnow())
        db.commit()
        db.refresh(db_apartment)
    return db_apartment

def delete_apartment(db: Session, apartmentId: int):
    db_apartment = db.query(models.Apartment).filter(models.Apartment.id == apartmentId).first()
    if db_apartment:
        db.delete(db_apartment)
        db.commit()
        return True
    return False

def update_apartment_status(db: Session, apartmentId: int, status: str):
    """Update an apartment's status"""
    db_apartment = db.query(models.Apartment).filter(models.Apartment.id == apartmentId).first()
    if db_apartment:
        setattr(db_apartment, "status", status)
        setattr(db_apartment, "updatedAt", datetime.utcnow())
        db.commit()
        db.refresh(db_apartment)
    return db_apartment

async def save_apartment_images(apartmentId: int, files: List[UploadFile]):
    """Save multiple apartment images and return the URLs."""
    imageUrls = []
    for file in files:
        imageUrl = await save_apartment_image(apartmentId, file)
        imageUrls.append(imageUrl)
    return imageUrls

async def save_apartment_image(apartmentId: int, file: UploadFile):
    """Save a single apartment image and return the URL."""
    # Create directory for apartment images if it doesn't exist
    upload_dir = f"static/apartments/{apartmentId}"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    filename = f"{uuid.uuid4()}{os.path.splitext(file.filename)[1] if file.filename else '.jpg'}"
    file_path = f"{upload_dir}/{filename}"
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Return the URL path
    return f"/apartments/{apartmentId}/{filename}"

def update_apartment_images(db: Session, apartmentId: int, imageUrls: List[str], append: bool = False):
    """Update apartment images in the database."""
    db_apartment = db.query(models.Apartment).filter(models.Apartment.id == apartmentId).first()
    
    if db_apartment:
        current_images = db_apartment.images or []    
        if append:
            # Add new images to existing ones
            updated_images = current_images + imageUrls
        else:
            # Replace images
            updated_images = imageUrls

        setattr(db_apartment, "images", updated_images)
        setattr(db_apartment, "updatedAt", datetime.utcnow())
        db.commit()
        db.refresh(db_apartment)
    return db_apartment

def add_apartment_image(db: Session, apartmentId: int, imageUrl: str):
    """Add a single image to an apartment."""
    db_apartment = db.query(models.Apartment).filter(models.Apartment.id == apartmentId).first()
    
    if db_apartment:
        current_images = db_apartment.images or []
        if current_images is None:
            current_images = [imageUrl]
        else:
            current_images.append(imageUrl)

        setattr(db_apartment, "images", current_images)
        setattr(db_apartment, "updatedAt", datetime.utcnow())
        db.commit()
        db.refresh(db_apartment)
    return db_apartment

def delete_apartment_image(db: Session, apartmentId: int, imageName: str):
    """Delete an image from an apartment."""
    db_apartment = db.query(models.Apartment).filter(models.Apartment.id == apartmentId).first()
    if db_apartment is not None and db_apartment.images is not None:
        imageUrl = f"/apartments/{apartmentId}/{imageName}"
        if imageUrl in db_apartment.images:
            db_apartment.images.remove(imageUrl)
            setattr(db_apartment, "updatedAt", datetime.utcnow())
            db.commit()
            
            # Try to delete the physical file
            try:
                os.remove(f"static{imageUrl}")
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

def get_available_apartments(db: Session):
    """Get apartments with status 'available'"""
    return db.query(models.Apartment).filter(
        models.Apartment.status == "available"
    ).all()

def get_apartment_tenants(db: Session, apartmentId: int, user_id: Optional[int] = None):
    """Get all tenants associated with an apartment through active leases."""
    # Query tenants through leases, filtered by apartment and user
    query = db.query(models.Lease).filter(
        models.Lease.apartmentId == apartmentId
    )
    if user_id is not None:
        query = query.filter(models.Lease.userId == user_id)
    
    leases = query.all()
    
    # Filter for active leases in Python
    active_leases = [lease for lease in leases if lease.isActive]
    
    # Get unique tenant IDs
    tenant_ids = {lease.tenantId for lease in active_leases}
    
    # Query tenants
    tenants = db.query(models.Tenant).filter(models.Tenant.id.in_(tenant_ids)).all()
    
    return tenants

def get_apartment_utilities(
    db: Session, 
    apartmentId: int, 
    type: Optional[str] = None,
    subtype: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    user_id: Optional[int] = None
):
    """Get utility readings for an apartment with optional filters."""
    query = db.query(models.UtilityReading).filter(
        models.UtilityReading.apartmentId == apartmentId
    )
    if user_id is not None:
        query = query.filter(models.UtilityReading.userId == user_id)
    
    if type:
        query = query.filter(models.UtilityReading.type == type)
    
    if subtype:
        query = query.filter(models.UtilityReading.subtype == subtype)
    
    if year:
        query = query.filter(
            func.extract('year', models.UtilityReading.readingDate) == year
        )
    
    if month:
        query = query.filter(
            func.extract('month', models.UtilityReading.readingDate) == month
        )
    
    return query.order_by(models.UtilityReading.readingDate.desc()).all()

def get_apartment_maintenance(
    db: Session, 
    apartmentId: int, 
    type: Optional[str] = None,
    fromDate: Optional[datetime] = None,
    toDate: Optional[datetime] = None,
    user_id: Optional[int] = None
):
    """Get maintenance records for an apartment with optional filters."""
    query = db.query(models.MaintenanceRecord).filter(
        models.MaintenanceRecord.apartmentId == apartmentId
    )
    if user_id is not None:
        query = query.filter(models.MaintenanceRecord.userId == user_id)
    
    if type:
        query = query.filter(models.MaintenanceRecord.type == type)
    
    if fromDate:
        query = query.filter(models.MaintenanceRecord.date >= fromDate)
    
    if toDate:
        query = query.filter(models.MaintenanceRecord.date <= toDate)
    
    return query.order_by(models.MaintenanceRecord.date.desc()).all()

def get_apartment_leases(
    db: Session, 
    apartmentId: int, 
    isActive: Optional[bool] = None,
    user_id: Optional[int] = None
):
    """Get leases for an apartment with optional active filter."""
    query = db.query(models.Lease).filter(
        models.Lease.apartmentId == apartmentId
    )
    if user_id is not None:
        query = query.filter(models.Lease.userId == user_id)
    
    leases = query.order_by(models.Lease.startDate.desc()).all()
    
    if isActive is not None:
        leases = [lease for lease in leases if lease.isActive == isActive]
        
    return leases

def get_apartment_invoices(
    db: Session, 
    apartmentId: int, 
    isPaid: Optional[bool] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    user_id: Optional[int] = None
):
    """Get invoices for an apartment with optional filters."""
    query = db.query(models.Invoice).filter(
        models.Invoice.apartmentId == apartmentId
    )
    if user_id is not None:
        query = query.filter(models.Invoice.userId == user_id)
    
    if isPaid is not None:
        query = query.filter(models.Invoice.isPaid == isPaid)
    
    if year:
        query = query.filter(models.Invoice.year == year)
    
    if month:
        query = query.filter(models.Invoice.month == month)
    
    return query.order_by(models.Invoice.issueDate.desc()).all()




# ----- Tenant Services -----

def get_tenants(db: Session, skip: int = 0, limit: int = 100, user_id: Optional[int] = None):
    """Ottiene tutti i tenant con query ORM ottimizzata."""
    try:
        # Forza un commit e svuota completamente la cache
        db.commit()
        db.expire_all()
        
        # Usa query ORM standard che è più affidabile
        query = db.query(models.Tenant)
        if hasattr(models.Tenant, "deletedAt"):
            query = query.filter(models.Tenant.deletedAt.is_(None))
        if user_id is not None:
            query = query.filter(models.Tenant.userId == user_id)
        return query.order_by(models.Tenant.id.desc()).offset(skip).limit(limit).all()
    except Exception as e:
        print(f"Errore nella funzione get_tenants: {str(e)}")
        # In caso di errore, riprova con una query più semplice
        return db.query(models.Tenant).all()

def get_tenant(db: Session, tenantId: int, user_id: Optional[int] = None):
    query = db.query(models.Tenant).filter(models.Tenant.id == tenantId)
    if user_id is not None:
        query = query.filter(models.Tenant.userId == user_id)
    return query.first()

def create_tenant(db: Session, tenant: schemas.TenantCreate, user_id: Optional[int] = None):
    # Convert Pydantic model to dict
    tenant_data = tenant.dict() if hasattr(tenant, "dict") else dict(tenant)
    
    # Handle nested dict for communication_preferences
    if "communicationPreferences" in tenant_data:
        if hasattr(tenant_data["communicationPreferences"], "dict"):
            tenant_data["communicationPreferences"] = tenant_data["communicationPreferences"].dict()
    
    # Associa l'utente se fornito (multi-tenancy)
    if user_id is not None:
        tenant_data["userId"] = user_id

    db_tenant = models.Tenant(**tenant_data)
    db.add(db_tenant)
    
    # Esegui flush prima del commit per assicurarti che tutte le operazioni siano completate
    db.flush()
    db.commit()
    
    # Ricarica dal database per assicurarti di avere la versione più recente
    db.refresh(db_tenant)
    return db_tenant

def update_tenant(db: Session, tenantId: int, tenant: schemas.TenantCreate):
    db_tenant = db.query(models.Tenant).filter(models.Tenant.id == tenantId).first()
    if db_tenant:
        # Convert tenant data to dict
        tenant_data = tenant.dict()
        # Handle nested dict for communication_preferences
        if hasattr(tenant_data["communicationPreferences"], "dict"):
            tenant_data["communicationPreferences"] = tenant_data["communicationPreferences"].dict()
        
        for key, value in tenant_data.items():
            setattr(db_tenant, key, value)
        
        setattr(db_tenant, "updatedAt", datetime.utcnow())
        db.commit()
        db.refresh(db_tenant)
    return db_tenant

def delete_tenant(db: Session, tenantId: int):
    """Delete a tenant and all associated files (Local + R2)."""
    db_tenant = db.query(models.Tenant).filter(models.Tenant.id == tenantId).first()
    if db_tenant:
        # 1. Elimina cartella locale (Legacy)
        try:
            tenant_dir = f"static/tenants/{tenantId}"
            if os.path.exists(tenant_dir):
                shutil.rmtree(tenant_dir)
                print(f"Deleted local tenant directory: {tenant_dir}")
        except Exception as e:
            print(f"Error deleting local tenant directory: {e}")
        
        # 2. Elimina cartella R2 (Nuovo)
        try:
            from app.services.r2_manager import R2Manager
            r2 = R2Manager()
            # La cartella R2 è 'documenti_inquilini/{id}/'
            r2.delete_folder(f"{tenantId}/", "inquilino")
        except Exception as e:
             print(f"Error deleting R2 tenant folder: {e}")

        # Elimina il tenant dal database
        db.delete(db_tenant)
        db.commit()
        return True
    return False

def update_tenant_communication_preferences(db: Session, tenantId: int, preferences: schemas.CommunicationPreferences):
    db_tenant = db.query(models.Tenant).filter(models.Tenant.id == tenantId).first()
    if db_tenant:
        setattr(db_tenant, "communicationPreferences", preferences.dict())
        setattr(db_tenant, "updatedAt", datetime.utcnow())
        db.commit()
        db.refresh(db_tenant)
    return db_tenant

# In service.py
async def save_tenant_document(tenantId: int, file: UploadFile, doc_type: str):
    """Salva in modo efficiente il documento di un tenant e restituisce l'URL."""
    # Validazione del tipo di file
    content_type = file.content_type
    if not content_type or not content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Il file deve essere un'immagine")
    
    # Crea directory con permessi corretti
    upload_dir = f"static/tenants/{tenantId}/documents"
    os.makedirs(upload_dir, exist_ok=True, mode=0o755)
    
    # Genera nome file più univoco per evitare collisioni
    timestamp = int(time.time())
    random_uuid = uuid.uuid4().hex
    extension = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    
    filename = f"{doc_type}_{timestamp}_{random_uuid}{extension}"
    file_path = f"{upload_dir}/{filename}"
    
    try:
        # Usa una copia temporanea del file prima di spostarlo nella posizione finale
        temp_path = f"{file_path}.temp"
        
        # Utilizzare aiofiles per operazioni asincrone più efficienti
        async with aiofiles.open(temp_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        
        # Verifica che il file temporaneo sia stato scritto correttamente
        if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            raise HTTPException(status_code=500, detail="Errore durante il salvataggio del file")
        
        # Rinomina il file temporaneo nel nome finale (operazione atomica)
        os.rename(temp_path, file_path)
        
        # Verifica il tipo di file (prevenire upload di file dannosi mascherati da immagini)
        file_type = imghdr.what(file_path)
        if not file_type:
            os.remove(file_path)
            raise HTTPException(status_code=400, detail="File non valido o non è un'immagine")
            
    except Exception as e:
        # Gestione errori con pulizia
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Errore durante il salvataggio: {str(e)}")
    
    # Prepara l'URL con parametro di cache-busting
    file_url = f"/tenants/{tenantId}/documents/{filename}?v={timestamp}"
    return file_url

def update_tenant_document(db: Session, tenantId: int, doc_url: str, doc_type: str):
    """Aggiorna il riferimento all'immagine del documento in modo atomico."""
    db_tenant = db.query(models.Tenant).filter(models.Tenant.id == tenantId).first()
    if not db_tenant:
        raise HTTPException(status_code=404, detail="Tenant non trovato")
    
    # Inizia una transazione esplicita per garantire l'atomicità
    try:
        # Salva l'URL precedente
        old_url = None
        if doc_type == "front":
            old_url = db_tenant.documentFrontImage
            db_tenant.documentFrontImage = doc_url
        elif doc_type == "back":
            old_url = db_tenant.documentBackImage
            db_tenant.documentBackImage = doc_url
        else:
            raise ValueError(f"Tipo di documento non valido: {doc_type}")
        
        db_tenant.updatedAt = datetime.utcnow()
        db.commit()
        
        # Elimina il vecchio file dopo aver aggiornato il DB con successo
        if old_url and old_url != doc_url and old_url != "":
            try:
                # Estrai il percorso del file senza parametri di query
                old_path = old_url.split('?')[0]
                old_file_path = f"static{old_path}"
                if os.path.exists(old_file_path) and os.path.isfile(old_file_path):
                    os.remove(old_file_path)
                    print(f"File eliminato: {old_file_path}")
                else:
                    print(f"File non trovato: {old_file_path}")
            except Exception as e:
                # Logga l'errore ma non interrompere l'operazione principale
                print(f"Errore nella pulizia del file precedente: {e}")
        
        return db_tenant
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Errore durante l'aggiornamento: {str(e)}")
    
async def delete_tenant_document(db: Session, tenantId: int, doc_type: str):
    """Elimina l'immagine del documento in modo sicuro e atomico."""
    db_tenant = db.query(models.Tenant).filter(models.Tenant.id == tenantId).first()
    if not db_tenant:
        raise HTTPException(status_code=404, detail="Tenant non trovato")
    
    try:
        # Ottieni il percorso del file
        file_url = None
        if doc_type == "front" and db_tenant.documentFrontImage:
            file_url = db_tenant.documentFrontImage
            # Aggiorna il tenant nel database (rimuovi il riferimento)
            db_tenant.documentFrontImage = ""
        elif doc_type == "back" and db_tenant.documentBackImage:
            file_url = db_tenant.documentBackImage
            # Aggiorna il tenant nel database (rimuovi il riferimento)
            db_tenant.documentBackImage = ""
        else:
            return {"detail": "Nessun documento da eliminare"}
        
        db_tenant.updatedAt = datetime.utcnow()
        db.commit()
        
        # Elimina il file fisicamente
        if file_url:
            # Rimuovi eventuali parametri di query dall'URL
            clean_url = file_url.split('?')[0]
            file_path = f"static{clean_url}"
            if os.path.exists(file_path) and os.path.isfile(file_path):
                os.remove(file_path)
        
        return {"detail": "Documento eliminato con successo", "success": True}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Errore durante l'eliminazione: {str(e)}")
    
def create_tenant_without_commit(db: Session, tenant: schemas.TenantCreate, user_id: Optional[int] = None):
    """Crea un tenant senza fare commit della transazione."""
    tenant_data = tenant.dict() if hasattr(tenant, "dict") else dict(tenant)
    
    if "communicationPreferences" in tenant_data:
        if hasattr(tenant_data["communicationPreferences"], "dict"):
            tenant_data["communicationPreferences"] = tenant_data["communicationPreferences"].dict()
    
    # Associa l'utente se fornito (multi-tenancy)
    if user_id is not None:
        tenant_data["userId"] = user_id

    db_tenant = models.Tenant(**tenant_data)
    db.add(db_tenant)
    db.flush()  # Genera l'ID senza fare commit
    return db_tenant

def get_tenant_leases(db: Session, tenantId: int, isActive: Optional[bool] = None, user_id: Optional[int] = None):
    """Get leases for a tenant with optional active filter."""
    query = db.query(models.Lease).filter(
        models.Lease.tenantId == tenantId
    )
    if user_id is not None:
        query = query.filter(models.Lease.userId == user_id)
    
    leases = query.order_by(models.Lease.startDate.desc()).all()
    
    if isActive is not None:
        leases = [lease for lease in leases if lease.isActive == isActive]
        
    return leases

def get_tenant_invoices(
    db: Session, 
    tenantId: int, 
    isPaid: Optional[bool] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    user_id: Optional[int] = None
):
    """Get invoices for a tenant with optional filters."""
    query = db.query(models.Invoice).filter(
        models.Invoice.tenantId == tenantId
    )
    if user_id is not None:
        query = query.filter(models.Invoice.userId == user_id)
    
    if isPaid is not None:
        query = query.filter(models.Invoice.isPaid == isPaid)
    
    if year:
        query = query.filter(models.Invoice.year == year)
    
    if month:
        query = query.filter(models.Invoice.month == month)
    
    return query.order_by(models.Invoice.issueDate.desc()).all()

def get_tenant_payment_history(db: Session, tenantId: int, user_id: Optional[int] = None):
    """Get payment history for a tenant."""
    # This query gets all payment records for invoices associated with this tenant
    query = db.query(models.PaymentRecord).join(
        models.Invoice,
        models.PaymentRecord.invoiceId == models.Invoice.id
    ).filter(
        models.Invoice.tenantId == tenantId
    )
    if user_id is not None:
        query = query.filter(models.Invoice.userId == user_id)
    return query.order_by(models.PaymentRecord.paymentDate.desc()).all()

def search_tenants(db: Session, query: str, user_id: Optional[int] = None):
    """Search tenants by name, email, or document number."""
    search = f"%{query}%"
    q = db.query(models.Tenant).filter(
        or_(
            models.Tenant.firstName.ilike(search),
            models.Tenant.lastName.ilike(search),
            models.Tenant.email.ilike(search),
            models.Tenant.documentNumber.ilike(search)
        )
    )
    if user_id is not None:
        q = q.filter(models.Tenant.userId == user_id)
    return q.all()



    # ----- Lease Services -----

def get_leases(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    status: Optional[str] = None,
    tenantId: Optional[int] = None,
    apartmentId: Optional[int] = None,
    user_id: Optional[int] = None
):
    """Get leases with optional filters."""
    query = db.query(models.Lease)
    if hasattr(models.Lease, "deletedAt"):
        query = query.filter(models.Lease.deletedAt.is_(None))
    if user_id is not None:
        query = query.filter(models.Lease.userId == user_id)
    
    if tenantId is not None:
        query = query.filter(models.Lease.tenantId == tenantId)
    
    if apartmentId is not None:
        query = query.filter(models.Lease.apartmentId == apartmentId)
    
    all_leases = query.offset(skip).limit(limit).all()
    
    if status is not None:
        all_leases = [lease for lease in all_leases if lease.status == status]
        
    return all_leases

def get_lease(db: Session, leaseId: int, user_id: Optional[int] = None):
    """Get a specific lease by ID."""
    query = db.query(models.Lease).filter(models.Lease.id == leaseId)
    if hasattr(models.Lease, "deletedAt"):
        query = query.filter(models.Lease.deletedAt.is_(None))
    if user_id is not None:
        query = query.filter(models.Lease.userId == user_id)
    return query.first()

def get_lease_payment_history(db: Session, lease_id: int, page: int = 1, size: int = 20, user_id: Optional[int] = None):
    """Get optimized payment history for a lease (invoice payments only)."""
    # 1. Recupera pagamenti fatture associati al contratto
    query = db.query(
        models.PaymentRecord, 
        models.Invoice.invoiceNumber,
        models.Invoice.month,
        models.Invoice.year
    ).join(
        models.Invoice, models.Invoice.id == models.PaymentRecord.invoiceId
    ).filter(
        models.Invoice.leaseId == lease_id
    )
    
    if user_id is not None:
        query = query.filter(models.PaymentRecord.userId == user_id)
        
    # Applica ordinamento per data decrescente
    query = query.order_by(models.PaymentRecord.paymentDate.desc())
    
    # Paginazione
    total = query.count()
    start = (page - 1) * size
    results = query.offset(start).limit(size).all()
    
    # 2. Formatta i dati
    items = []
    for record, inv_num, inv_month, inv_year in results:
        items.append({
            "id": record.id,
            "date": record.paymentDate,
            "amount": record.amount,
            "method": record.paymentMethod,
            "type": "invoice",
            "reference": record.reference or f"Fattura {inv_num}",
            "notes": record.notes,
            "invoiceId": record.invoiceId,
            "invoiceNumber": inv_num,
            "invoiceType": inv_num.split('-')[0] if inv_num else 'INV',
            "invoiceMonth": inv_month,
            "invoiceYear": inv_year
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size
    }

def create_lease(db: Session, lease: schemas.LeaseCreate, user_id: Optional[int] = None):
    """Create a new lease."""
    data = lease.dict()
    if user_id is not None:
        data["userId"] = user_id
    
    # Estrai le letture iniziali dal campo annidato initialReadings
    initial_readings = data.pop("initialReadings", None)
    if initial_readings:
        apt_id = data.get("apartmentId")
        start_date = data.get("startDate")
        
        # Mappa dei tipi utenza e dei relativi campi nel payload
        utility_map = {
            "electricity": ("electricityReadingId", "electricityValue", None),
            "water": ("waterReadingId", "waterValue", None),
            "gas": ("gasReadingId", "gasValue", None),
            "electricity_laundry": ("electricityLaundryReadingId", "electricityLaundryValue", "laundry")
        }

        for u_type, (id_field, val_field, subtype) in utility_map.items():
            r_id = initial_readings.get(id_field)
            r_val = initial_readings.get(val_field)

            if r_id:
                # Se abbiamo l'ID, lo usiamo direttamente
                data[id_field] = r_id
            elif r_val is not None:
                # Se abbiamo il valore, creiamo una lettura di sistema (baseline)
                new_reading = models.UtilityReading(
                    userId=user_id,
                    apartmentId=apt_id,
                    type=u_type if u_type != "electricity_laundry" else "electricity",
                    subtype=subtype,
                    readingDate=start_date,
                    previousReading=r_val,
                    currentReading=r_val,
                    consumption=0.0,
                    unitCost=0.0,
                    totalCost=0.0,
                    isSpecialReading=True,
                    notes="Lettura iniziale di sistema (Baseline)"
                )
                db.add(new_reading)
                db.flush() # Per ottenere l'ID senza fare commit
                data[id_field] = new_reading.id
    
    db_lease = models.Lease(**data)
    db.add(db_lease)
    db.commit()
    db.refresh(db_lease)
    return db_lease

def update_lease(db: Session, leaseId: int, lease: schemas.LeaseCreate):
    """Update an existing lease."""
    db_lease = db.query(models.Lease).filter(models.Lease.id == leaseId).first()
    if db_lease:
        for key, value in lease.dict().items():
            setattr(db_lease, key, value)
        
        setattr(db_lease, "updatedAt", datetime.utcnow())
        db.commit()
        db.refresh(db_lease)
    return db_lease

def delete_lease(db: Session, leaseId: int):
    """Delete a lease and its associated documents (Local + R2)."""
    db_lease = db.query(models.Lease).filter(models.Lease.id == leaseId).first()
    if db_lease:
        # 1. Elimina documenti associati
        lease_docs = db.query(models.LeaseDocument).filter(models.LeaseDocument.leaseId == leaseId).all()
        
        try:
            from app.services.r2_manager import R2Manager
            r2 = R2Manager()
            for doc in lease_docs:
                 if doc.url:
                     # Se è un URL R2 (non inizia con /), elimina da R2
                     if not doc.url.startswith('/'):
                         r2.delete_file(doc.url, 'contratto')
                     # Se è locale
                     else:
                         try:
                            file_path = f"static/leases/{leaseId}/documents/{os.path.basename(doc.url)}"
                            if os.path.exists(file_path):
                                os.remove(file_path)
                         except:
                             pass
            
            # 1.1 Elimina cartella fatture da R2 (Bucket prospetti-mensili)
            r2.delete_folder(f"{leaseId}/", 'prospetto')
        except Exception as e:
            print(f"Error deleting lease documents/invoices from R2: {e}")

        # 2. Elimina eventuali cartelle locali (Legacy)
        try:
            lease_dir = f"static/leases/{leaseId}"
            if os.path.exists(lease_dir):
                shutil.rmtree(lease_dir)
        except:
             pass

        db.delete(db_lease)
        db.commit()
        return True
    return False

def get_expiring_leases(db: Session, days_threshold: int = 30):
    """Get leases that are expiring within the specified number of days."""
    today = datetime.utcnow().date()
    expiry_date = today + timedelta(days=days_threshold)
    
    # Fetch all potentially relevant leases from the DB
    leases = db.query(models.Lease).filter(
        models.Lease.endDate <= expiry_date,
        models.Lease.endDate >= today
    ).order_by(models.Lease.endDate).all()
    
    # Filter for active leases in Python
    active_expiring_leases = [lease for lease in leases if lease.isActive]
    
    return active_expiring_leases

async def save_lease_document(leaseId: int, file: UploadFile):
    """Save a lease document file and return the URL."""
    # Create directory for lease documents if it doesn't exist
    upload_dir = f"static/leases/{leaseId}/documents"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    filename = f"{uuid.uuid4()}{os.path.splitext(file.filename)[1] if file.filename else '.jpg'}"
    file_path = f"{upload_dir}/{filename}"
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Return the URL path
    return f"/leases/{leaseId}/documents/{filename}"

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

def get_lease_documents(db: Session, leaseId: int, user_id: Optional[int] = None):
    """Get all documents for a specific lease."""
    query = db.query(models.LeaseDocument).filter(models.LeaseDocument.leaseId == leaseId)
    if user_id is not None:
        query = query.join(models.Lease).filter(models.Lease.userId == user_id)
    return query.all()

def delete_lease_document(db: Session, document_id: int):
    """Delete a lease document (Local or R2)."""
    db_document = db.query(models.LeaseDocument).filter(models.LeaseDocument.id == document_id).first()
    if db_document:
        # 1. Tenta eliminazione da R2 se non è path locale o se R2 è configurato
        if db_document.url and not db_document.url.startswith('/'):
            try:
                from app.services.r2_manager import R2Manager
                r2 = R2Manager()
                r2.delete_file(db_document.url, 'contratto')
            except Exception as e:
                print(f"Error deleting from R2: {e}")

        # 2. Tenta eliminazione fisica (Legacy/Local)
        try:
            # Gestione sicura del path
            if db_document.url and db_document.url.startswith('/'):
                 file_path = f"static{db_document.url.split('?')[0]}"
            else:
                 # Fallback per vecchi path o struttura
                 file_path = f"static/leases/{db_document.leaseId}/documents/{os.path.basename(str(db_document.url or ''))}"
            
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
        
        db.delete(db_document)
        db.commit()
        return True
    return False


def search_leases(db: Session, query: str, user_id: Optional[int] = None):
    """Search leases by associated tenant or apartment."""
    search = f"%{query}%"
    
    # Search by tenant name or apartment name
    q = db.query(models.Lease).join(
        models.Tenant, models.Lease.tenantId == models.Tenant.id
    ).join(
        models.Apartment, models.Lease.apartmentId == models.Apartment.id
    ).filter(
        or_(
            models.Tenant.firstName.ilike(search),
            models.Tenant.lastName.ilike(search),
            models.Apartment.name.ilike(search)
        )
    )
    if user_id is not None:
        q = q.filter(models.Lease.userId == user_id)
    return q.all()





# ----- Utility Reading Services -----

def get_utility_readings(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    apartmentId: Optional[int] = None,
    type: Optional[str] = None,
    subtype: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    isPaid: Optional[bool] = None,
    user_id: Optional[int] = None
):
    """Get utility readings with optional filters."""
    query = db.query(models.UtilityReading)
    if user_id is not None:
        query = query.filter(models.UtilityReading.userId == user_id)
    if hasattr(models.UtilityReading, "deletedAt"):
        query = query.filter(models.UtilityReading.deletedAt.is_(None))
    
    if apartmentId is not None:
        query = query.filter(models.UtilityReading.apartmentId == apartmentId)
    
    if type is not None:
        query = query.filter(models.UtilityReading.type == type)
    
    if subtype is not None:
        query = query.filter(models.UtilityReading.subtype == subtype)
    
    if year is not None:
        query = query.filter(func.extract('year', models.UtilityReading.readingDate) == year)
    
    if month is not None:
        query = query.filter(func.extract('month', models.UtilityReading.readingDate) == month)
    
    if isPaid is not None:
        query = query.filter(models.UtilityReading.isPaid == isPaid)
    
    return query.order_by(models.UtilityReading.readingDate.desc()).offset(skip).limit(limit).all()

def get_utility_reading(db: Session, reading_id: int, user_id: Optional[int] = None):
    """Get a specific utility reading by ID."""
    query = db.query(models.UtilityReading).filter(models.UtilityReading.id == reading_id)
    if user_id is not None:
        query = query.filter(models.UtilityReading.userId == user_id)
    if hasattr(models.UtilityReading, "deletedAt"):
        query = query.filter(models.UtilityReading.deletedAt.is_(None))
    return query.first()

def get_last_utility_reading(db: Session, apartmentId: int, type: str, subtype: Optional[str] = None):
    """Get the last utility reading for a specific apartment and type."""
    query = db.query(models.UtilityReading).filter(
        models.UtilityReading.apartmentId == apartmentId,
        models.UtilityReading.type == type
    )
    
    if subtype is not None:
        query = query.filter(models.UtilityReading.subtype == subtype)
    
    return query.order_by(models.UtilityReading.readingDate.desc()).first()

def get_previous_utility_reading_for_chain(
    db: Session,
    *,
    apartmentId: int,
    type: str,
    subtype: Optional[str],
    readingDate: date,
    exclude_id: Optional[int] = None,
    user_id: Optional[int] = None,
):
    query = db.query(models.UtilityReading).filter(
        models.UtilityReading.apartmentId == apartmentId,
        models.UtilityReading.type == type,
        models.UtilityReading.readingDate < readingDate,
    )
    if user_id is not None:
        query = query.filter(models.UtilityReading.userId == user_id)
    if subtype is not None:
        query = query.filter(models.UtilityReading.subtype == subtype)
    if exclude_id is not None:
        query = query.filter(models.UtilityReading.id != exclude_id)
    if hasattr(models.UtilityReading, "deletedAt"):
        query = query.filter(models.UtilityReading.deletedAt.is_(None))
    return query.order_by(models.UtilityReading.readingDate.desc()).first()

def create_utility_reading(db: Session, reading: schemas.UtilityReadingCreate, user_id: Optional[int] = None):
    """Create a new utility reading."""
    data = reading.dict()
    if user_id is not None:
        data["userId"] = user_id
    db_reading = models.UtilityReading(**data)
    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)
    return db_reading

def update_utility_reading(db: Session, reading_id: int, reading: schemas.UtilityReadingCreate):
    db_reading = db.query(models.UtilityReading).filter(models.UtilityReading.id == reading_id).first()
    if not db_reading:
        return None

    update_data = reading.dict()
    for key, value in update_data.items():
        setattr(db_reading, key, value)

    prev = get_previous_utility_reading_for_chain(
        db,
        apartmentId=db_reading.apartmentId,
        type=db_reading.type,
        subtype=db_reading.subtype,
        readingDate=db_reading.readingDate,
        exclude_id=reading_id,
        user_id=db_reading.userId,
    )
    db_reading.previousReading = prev.currentReading if prev else 0.0

    if db_reading.currentReading < db_reading.previousReading:
        raise HTTPException(status_code=400, detail=f"Current reading must be >= previous ({db_reading.previousReading})")

    db_reading.consumption = db_reading.currentReading - db_reading.previousReading
    db_reading.totalCost = db_reading.consumption * db_reading.unitCost
    db_reading.updatedAt = datetime.utcnow()

    cascade_q = db.query(models.UtilityReading).filter(
        models.UtilityReading.apartmentId == db_reading.apartmentId,
        models.UtilityReading.type == db_reading.type,
        models.UtilityReading.readingDate > db_reading.readingDate,
        models.UtilityReading.userId == db_reading.userId,
    )
    if db_reading.subtype is not None:
        cascade_q = cascade_q.filter(models.UtilityReading.subtype == db_reading.subtype)
    if hasattr(models.UtilityReading, "deletedAt"):
        cascade_q = cascade_q.filter(models.UtilityReading.deletedAt.is_(None))
    subsequent_readings = cascade_q.order_by(models.UtilityReading.readingDate.asc()).all()

    prev_current = db_reading.currentReading
    for r in subsequent_readings:
        r.previousReading = prev_current
        if r.currentReading < r.previousReading:
            raise HTTPException(status_code=400, detail=f"Reading {r.id}: current ({r.currentReading}) < previous ({r.previousReading}) after cascade")
        r.consumption = r.currentReading - r.previousReading
        r.totalCost = r.consumption * r.unitCost
        r.updatedAt = datetime.utcnow()
        prev_current = r.currentReading

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

def get_utility_summary(db: Session, apartmentId: int, year: Optional[int] = None, user_id: Optional[int] = None):
    """Get utility summary for a specific apartment."""
    # Query utilities
    query = db.query(models.UtilityReading).filter(
        models.UtilityReading.apartmentId == apartmentId
    )
    if user_id is not None:
        query = query.filter(models.UtilityReading.userId == user_id)
    
    if year:
        query = query.filter(func.extract('year', models.UtilityReading.readingDate) == year)
    
    readings = query.order_by(models.UtilityReading.readingDate).all()
    
    # Group by month and year
    summary_dict = {}
    for reading in readings:
        reading_month = reading.readingDate.month
        reading_year = reading.readingDate.year
        key = f"{reading_year}-{reading_month}"
        
        if key not in summary_dict:
            summary_dict[key] = {
                "apartmentId": apartmentId,
                "month": reading_month,
                "year": reading_year,
                "electricity": {"consumption": 0, "cost": 0},
                "water": {"consumption": 0, "cost": 0},
                "gas": {"consumption": 0, "cost": 0},
                "totalCost": 0
            }
        
        # Add consumption and cost based on type
        if str(reading.type) == "electricity":
            summary_dict[key]["electricity"]["consumption"] += reading.consumption
            summary_dict[key]["electricity"]["cost"] += reading.totalCost
        elif str(reading.type) == "water":
            summary_dict[key]["water"]["consumption"] += reading.consumption
            summary_dict[key]["water"]["cost"] += reading.totalCost
        elif str(reading.type) == "gas":
            summary_dict[key]["gas"]["consumption"] += reading.consumption
            summary_dict[key]["gas"]["cost"] += reading.totalCost
        
        # Update total cost
        summary_dict[key]["totalCost"] += reading.totalCost
    
    # Convert dictionary to list
    summary_list = list(summary_dict.values())
    
    # Sort by year and month
    summary_list.sort(key=lambda x: (x["year"], x["month"]))
    
    return summary_list

def get_yearly_utility_statistics(db: Session, year: int, user_id: Optional[int] = None):
    """Get utility statistics for all apartments for a specific year."""
    # Query all readings for the year
    query = db.query(models.UtilityReading).filter(
        func.extract('year', models.UtilityReading.readingDate) == year
    )
    if user_id is not None:
        query = query.filter(models.UtilityReading.userId == user_id)
    readings = query.all()
    
    # Group by apartment and month
    stats_dict = {}
    for reading in readings:
        apartmentId = reading.apartmentId
        month = reading.readingDate.month
        key = f"{apartmentId}-{month}"
        
        if key not in stats_dict:
            apartment = db.query(models.Apartment).filter(models.Apartment.id == apartmentId).first()
            apartment_name = apartment.name if apartment else f"Apartment {apartmentId}"
            
            stats_dict[key] = {
                "month": month,
                "year": year,
                "apartmentId": apartmentId,
                "apartmentName": apartment_name,
                "electricity": 0,  # Solo elettricità principale
                "water": 0,
                "gas": 0,
                "electricityCost": 0,  # Solo costo elettricità principale
                "waterCost": 0,
                "gasCost": 0,
                "laundryElectricity": 0,  # Elettricità lavanderia
                "laundryElectricityCost": 0,  # Costo elettricità lavanderia
                "totalCost": 0
            }
        
        # Add consumption and cost based on type and subtype
        if str(reading.type) == "electricity":
            if reading.subtype == "laundry":
                # Elettricità lavanderia
                stats_dict[key]["laundryElectricity"] += reading.consumption
                stats_dict[key]["laundryElectricityCost"] += reading.totalCost
            else:
                # Elettricità principale (main o None)
                stats_dict[key]["electricity"] += reading.consumption
                stats_dict[key]["electricityCost"] += reading.totalCost
        elif str(reading.type) == "water":
            stats_dict[key]["water"] += reading.consumption
            stats_dict[key]["waterCost"] += reading.totalCost
        elif str(reading.type) == "gas":
            stats_dict[key]["gas"] += reading.consumption
            stats_dict[key]["gasCost"] += reading.totalCost
        
        # Update total cost
        stats_dict[key]["totalCost"] += reading.totalCost
    
    # Convert dictionary to list
    stats_list = list(stats_dict.values())
    
    # Sort by apartment ID and month
    stats_list.sort(key=lambda x: (x["apartmentId"], x["month"]))
    
    return stats_list

def get_apartment_consumption(db: Session, apartmentId: int, year: int, user_id: Optional[int] = None):
    """Get utility consumption data for a specific apartment and year."""
    # Query all readings for the apartment and year
    query = db.query(models.UtilityReading).filter(
        models.UtilityReading.apartmentId == apartmentId,
        func.extract('year', models.UtilityReading.readingDate) == year
    )
    if user_id is not None:
        query = query.filter(models.UtilityReading.userId == user_id)
    readings = query.all()
    
    # Get the apartment name
    apartment = db.query(models.Apartment).filter(models.Apartment.id == apartmentId).first()
    apartment_name = apartment.name if apartment else f"Apartment {apartmentId}"
    
    # Group by month
    monthly_data = {}
    for month in range(1, 13):
        monthly_data[month] = {
            "month": month,
            "monthName": [
                "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
            ][month - 1],
            "electricity": 0,  # Solo elettricità principale
            "water": 0,
            "gas": 0,
            "electricityCost": 0,  # Solo costo elettricità principale
            "waterCost": 0,
            "gasCost": 0,
            "laundryElectricity": 0,  # Elettricità lavanderia
            "laundryElectricityCost": 0,  # Costo elettricità lavanderia
            "totalCost": 0
        }
    
    for reading in readings:
        month = reading.readingDate.month
        
        # Add consumption and cost based on type and subtype
        if str(reading.type) == "electricity":
            if reading.subtype == "laundry":
                # Elettricità lavanderia
                monthly_data[month]["laundryElectricity"] += reading.consumption
                monthly_data[month]["laundryElectricityCost"] += reading.totalCost
            else:
                # Elettricità principale (main o None)
                monthly_data[month]["electricity"] += reading.consumption
                monthly_data[month]["electricityCost"] += reading.totalCost
        elif str(reading.type) == "water":
            monthly_data[month]["water"] += reading.consumption
            monthly_data[month]["waterCost"] += reading.totalCost
        elif str(reading.type) == "gas":
            monthly_data[month]["gas"] += reading.consumption
            monthly_data[month]["gasCost"] += reading.totalCost
        
        monthly_data[month]["totalCost"] += reading.totalCost
    
    # Calculate yearly totals
    yearly_totals = {
        "electricity": sum(month["electricity"] for month in monthly_data.values()),
        "water": sum(month["water"] for month in monthly_data.values()),
        "gas": sum(month["gas"] for month in monthly_data.values()),
        "laundryElectricity": sum(month["laundryElectricity"] for month in monthly_data.values()),
        "totalCost": sum(month["totalCost"] for month in monthly_data.values())
    }
    
    # Create the output structure
    result = {
        "apartmentId": apartmentId,
        "apartmentName": apartment_name,
        "monthlyData": list(monthly_data.values()),
        "yearlyTotals": yearly_totals
    }
    
    return result

def get_utility_statistics_overview(db: Session, year: Optional[int] = None, user_id: Optional[int] = None):
    """Get overall utility statistics."""
    from datetime import datetime
    
    if year is None:
        year = datetime.now().year
    
    # Query all readings for the year
    query = db.query(models.UtilityReading).filter(
        func.extract('year', models.UtilityReading.readingDate) == year
    )
    if user_id is not None:
        query = query.filter(models.UtilityReading.userId == user_id)
    readings = query.all()
    
    # Get all apartments
    apartments = db.query(models.Apartment).all()
    total_apartments = len(apartments)
    
    # Calculate totals
    total_consumption = {"electricity": 0, "water": 0, "gas": 0}
    total_costs = {"electricity": 0, "water": 0, "gas": 0, "total": 0}
    
    # Monthly trend data
    monthly_trend = {}
    for month in range(1, 13):
        monthly_trend[month] = {
            "month": month,
            "monthName": [
                "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
            ][month - 1],
            "totalConsumption": 0,
            "totalCost": 0
        }
    
    for reading in readings:
        month = reading.readingDate.month
        
        # Add to totals
        if str(reading.type) == "electricity":
            total_consumption["electricity"] += reading.consumption
            total_costs["electricity"] += reading.totalCost
        elif str(reading.type) == "water":
            total_consumption["water"] += reading.consumption
            total_costs["water"] += reading.totalCost
        elif str(reading.type) == "gas":
            total_consumption["gas"] += reading.consumption
            total_costs["gas"] += reading.totalCost
        
        total_costs["total"] += reading.totalCost
        
        # Add to monthly trend
        monthly_trend[month]["totalConsumption"] += reading.consumption
        monthly_trend[month]["totalCost"] += reading.totalCost
    
    # Calculate averages
    avg_divisor = max(total_apartments, 1)  # Avoid division by zero
    average_consumption = {
        "electricity": total_consumption["electricity"] / avg_divisor,
        "water": total_consumption["water"] / avg_divisor,
        "gas": total_consumption["gas"] / avg_divisor
    }
    
    return {
        "totalApartments": total_apartments,
        "totalConsumption": total_consumption,
        "totalCosts": total_costs,
        "averageConsumption": average_consumption,
        "monthlyTrend": list(monthly_trend.values())
    }

def sync_apartment_images_with_filesystem(db: Session, apartmentId: int):
    """Sincronizza le immagini dell'appartamento nel database con quelle fisicamente presenti nel filesystem."""
    db_apartment = db.query(models.Apartment).filter(models.Apartment.id == apartmentId).first()
    if not db_apartment:
        return None
    
    # Percorso della cartella delle immagini
    images_dir = f"static/apartments/{apartmentId}"
    
    # Ottieni le immagini dal database
    db_images = db_apartment.images or []
    
    # Ottieni le immagini fisicamente presenti nel filesystem
    existing_files = []
    if os.path.exists(images_dir) and os.path.isdir(images_dir):
        for filename in os.listdir(images_dir):
            file_path = os.path.join(images_dir, filename)
            if os.path.isfile(file_path):
                existing_files.append(f"/apartments/{apartmentId}/{filename}")
    
    # Trova le immagini che sono nel database ma non nel filesystem
    orphaned_images = [img for img in db_images if img not in existing_files]
    
    # Rimuovi le immagini orfane dal database
    if orphaned_images:
        print(f"Rimuovendo {len(orphaned_images)} immagini orfane per l'appartamento {apartmentId}: {orphaned_images}")
        updated_images = [img for img in db_images if img in existing_files]
        
        setattr(db_apartment, "images", updated_images)
        setattr(db_apartment, "updatedAt", datetime.utcnow())
        db.commit()
        db.refresh(db_apartment)
        
        return {
            "removed_orphaned_images": orphaned_images,
            "current_images": updated_images
        }
    
    return {
        "removed_orphaned_images": [],
        "current_images": db_images
    }

def sync_tenant_documents_with_filesystem(db: Session, tenantId: int):
    """Sincronizza i documenti del tenant nel database con quelli fisicamente presenti nel filesystem."""
    db_tenant = db.query(models.Tenant).filter(models.Tenant.id == tenantId).first()
    if not db_tenant:
        return None
    
    # Percorso della cartella dei documenti
    documents_dir = f"static/tenants/{tenantId}/documents"
    
    # Ottieni i documenti dal database
    front_image = db_tenant.documentFrontImage
    back_image = db_tenant.documentBackImage
    
    # Lista per tracciare i documenti orfani
    orphaned_documents = []
    updated_fields = {}
    
    # Verifica l'esistenza dell'immagine fronte
    if front_image:
        # Rimuovi eventuali parametri di query dall'URL
        clean_front_url = front_image.split('?')[0]
        front_file_path = f"static{clean_front_url}"
        
        if not os.path.exists(front_file_path) or not os.path.isfile(front_file_path):
            orphaned_documents.append(f"front: {front_image}")
            updated_fields["documentFrontImage"] = None
    
    # Verifica l'esistenza dell'immagine retro
    if back_image:
        # Rimuovi eventuali parametri di query dall'URL
        clean_back_url = back_image.split('?')[0]
        back_file_path = f"static{clean_back_url}"
        
        if not os.path.exists(back_file_path) or not os.path.isfile(back_file_path):
            orphaned_documents.append(f"back: {back_image}")
            updated_fields["documentBackImage"] = None
    
    # Aggiorna il database se ci sono documenti orfani
    if orphaned_documents:
        print(f"Rimuovendo {len(orphaned_documents)} documenti orfani per il tenant {tenantId}: {orphaned_documents}")
        
        # Applica gli aggiornamenti al database
        for field, value in updated_fields.items():
            setattr(db_tenant, field, value)
        
        setattr(db_tenant, "updatedAt", datetime.utcnow())
        db.commit()
        db.refresh(db_tenant)
        
        return {
            "removed_orphaned_documents": orphaned_documents,
            "updated_fields": updated_fields,
            "current_front_image": db_tenant.documentFrontImage,
            "current_back_image": db_tenant.documentBackImage
        }
    
    return {
        "removed_orphaned_documents": [],
        "updated_fields": {},
        "current_front_image": front_image,
        "current_back_image": back_image
    }

    # ----- Invoice Services -----

def get_invoices(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    tenant_id: Optional[int] = None,
    apartment_id: Optional[int] = None,
    lease_id: Optional[int] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    sort_by: str = "issueDate",
    sort_order: str = "desc",
    user_id: Optional[int] = None
):
    """Get invoices with optional filters."""
    from sqlalchemy.orm import joinedload
    query = db.query(models.Invoice).options(
        joinedload(models.Invoice.items),
        joinedload(models.Invoice.payments)
    )
    if hasattr(models.Invoice, "deletedAt"):
        query = query.filter(models.Invoice.deletedAt.is_(None))
    if user_id is not None:
        query = query.filter(models.Invoice.userId == user_id)
    
    # Apply filters
    if status:
        if status == "paid":
            query = query.filter(models.Invoice.isPaid == True)
        elif status == "unpaid":
            query = query.filter(models.Invoice.isPaid == False)
        elif status == "overdue":
            query = query.filter(
                models.Invoice.isPaid == False,
                models.Invoice.dueDate < datetime.utcnow().date()
            )
    
    if tenant_id:
        query = query.filter(models.Invoice.tenantId == tenant_id)
    
    if apartment_id:
        query = query.filter(models.Invoice.apartmentId == apartment_id)
    
    if lease_id:
        query = query.filter(models.Invoice.leaseId == lease_id)
    
    if month:
        query = query.filter(models.Invoice.month == month)
    
    if year:
        query = query.filter(models.Invoice.year == year)
    
    if start_date:
        query = query.filter(models.Invoice.issueDate >= start_date)
    
    if end_date:
        query = query.filter(models.Invoice.issueDate <= end_date)
    
    if search:
        query = query.filter(models.Invoice.invoiceNumber.ilike(f"%{search}%"))
    
    # Apply sorting
    if sort_by == "issueDate":
        sort_column = models.Invoice.issueDate
    elif sort_by == "dueDate":
        sort_column = models.Invoice.dueDate
    elif sort_by == "total":
        sort_column = models.Invoice.total
    elif sort_by == "invoiceNumber":
        sort_column = models.Invoice.invoiceNumber
    else:
        sort_column = models.Invoice.issueDate
    
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
    return query.offset(skip).limit(limit).all()

def get_invoice(db: Session, invoice_id: int):
    """Get a specific invoice by ID."""
    return db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()

def create_invoice(db: Session, invoice: schemas.InvoiceCreate, user_id: Optional[int] = None):
    """Create a new invoice."""
    # Generate invoice number if not provided
    if not invoice.invoiceNumber:
        invoice.invoiceNumber = generate_invoice_number(db)
    
    # Create invoice items list
    items_to_create = list(invoice.items)
    
    # subtotal = sum of RENT items only as per user request
    subtotal = sum(item.amount for item in items_to_create if item.type == 'rent')
    
    # total = sum of all items (rent + utilities + fixed costs)
    total = sum(item.amount for item in items_to_create)
    
    # Create invoice
    db_invoice = models.Invoice(
        leaseId=invoice.leaseId,
        tenantId=invoice.tenantId,
        apartmentId=invoice.apartmentId,
        invoiceNumber=invoice.invoiceNumber,
        month=invoice.month,
        year=invoice.year,
        issueDate=invoice.issueDate,
        dueDate=invoice.dueDate,
        subtotal=subtotal,
        total=total,
        notes=invoice.notes,
        userId=user_id if user_id is not None else None
    )

    # Impostazioni automazione reminder
    if user_id is not None:
        defaults = get_defaults(db, user_id=user_id)
        if defaults.automationType == models.InvoiceAutomationType.immediate:
            db_invoice.reminderDate = db_invoice.issueDate
            db_invoice.reminderSent = False
        elif defaults.automationType == models.InvoiceAutomationType.scheduled:
            db_invoice.reminderDate = db_invoice.issueDate + timedelta(days=defaults.automationDays)
            db_invoice.reminderSent = False
        else: # manual
            db_invoice.reminderDate = None
            db_invoice.reminderSent = False
    
    db.add(db_invoice)
    db.flush()  # Flush to get db_invoice.id without committing
    
    # Create invoice items
    for item in items_to_create:
        db_item = models.InvoiceItem(
            invoiceId=db_invoice.id,
            description=item.description,
            amount=item.amount,
            type=item.type,
            userId=user_id if user_id is not None else None
        )
        db.add(db_item)
    
    db.commit()
    db.refresh(db_invoice)
    return db_invoice

def update_invoice(db: Session, invoice_id: int, invoice: schemas.InvoiceCreate, user_id: Optional[int] = None):
    """Update an existing invoice."""
    db_invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not db_invoice:
        return None
    
    # Update invoice fields
    for key, value in invoice.dict(exclude={'items'}).items():
        setattr(db_invoice, key, value)
    
    # Recalculate totals
    # subtotal = Rent items
    subtotal = sum(item.amount for item in invoice.items if item.type == 'rent')
    db_invoice.subtotal = subtotal
    
    # total = sum of all items
    db_invoice.total = sum(item.amount for item in invoice.items)
    db_invoice.updatedAt = datetime.utcnow()
    
    # Delete existing items and create new ones
    db.query(models.InvoiceItem).filter(models.InvoiceItem.invoiceId == invoice_id).delete()
    
    for item in invoice.items:
        db_item = models.InvoiceItem(
            invoiceId=invoice_id,
            description=item.description,
            amount=item.amount,
            type=item.type,
            userId=user_id if user_id is not None else db_invoice.userId
        )
        db.add(db_item)
    
    db.commit()
    db.refresh(db_invoice)
    return db_invoice

def delete_invoice(db: Session, invoice_id: int):
    """Delete an invoice and its generated PDF."""
    db_invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if db_invoice:
        # Elimina PDF generato se esiste
        try:
            pdf_path = f"static/invoices/{db_invoice.invoiceNumber}.pdf"
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        except Exception as e:
            print(f"Error deleting local invoice PDF: {e}")

        # 2. Elimina da R2 (Bucket prospetti-mensili, path: leaseId/invoiceNumber.pdf)
        try:
            from app.services.r2_manager import R2Manager
            r2 = R2Manager()
            r2.delete_file(f"{db_invoice.leaseId}/{db_invoice.invoiceNumber}.pdf", 'prospetto')
        except Exception as e:
            print(f"Error deleting R2 invoice PDF: {e}")

        db.delete(db_invoice)
        db.commit()
        return True
    return False

def mark_invoice_as_paid(db: Session, invoice_id: int, payment_data: dict):
    """Mark an invoice as paid."""
    db_invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not db_invoice:
        return None
    
    db_invoice.isPaid = True
    db_invoice.updatedAt = datetime.utcnow()
    
    # Create a PaymentRecord if needed or if data is provided
    # This aligns with the new system where root payment fields are removed
    payment_record = models.PaymentRecord(
        invoiceId=invoice_id,
        amount=db_invoice.total, # Default to total if not provided
        paymentDate=payment_data.get('payment_date', datetime.utcnow().date()),
        paymentMethod=payment_data.get('payment_method', 'bank_transfer'),
        reference=payment_data.get('reference', ''),
        notes=payment_data.get('notes', 'Marked as paid from invoice'),
        userId=db_invoice.userId
    )
    db.add(payment_record)
    
    db.commit()
    db.refresh(db_invoice)
    return db_invoice

def add_payment_record(db: Session, invoice_id: int, payment_record: schemas.PaymentRecordCreate, user_id: Optional[int] = None):
    """Add a payment record to an invoice."""
    db_invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not db_invoice:
        return None
    
    db_invoice.isPaid = True
    db_invoice.updatedAt = datetime.utcnow()
    
    db_payment = models.PaymentRecord(
        invoiceId=invoice_id,
        amount=payment_record.amount,
        paymentDate=payment_record.paymentDate,
        paymentMethod=payment_record.paymentMethod,
        reference=payment_record.reference,
        notes=payment_record.notes,
        userId=user_id if user_id is not None else None
    )
    
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment

def get_invoice_payment_records(db: Session, invoice_id: int, user_id: Optional[int] = None):
    """Get all payment records for an invoice."""
    query = db.query(models.Invoice).filter(models.Invoice.id == invoice_id)
    if user_id is not None:
        query = query.filter(models.Invoice.userId == user_id)
    db_invoice = query.first()
    if not db_invoice:
        return None
    
    return db.query(models.PaymentRecord).filter(
        models.PaymentRecord.invoiceId == invoice_id
    ).order_by(models.PaymentRecord.paymentDate.desc()).all()

def send_invoice_reminder(db: Session, invoice_id: int, reminder_data: dict, user_id: Optional[int] = None):
    """Send a reminder for an invoice."""
    query = db.query(models.Invoice).filter(models.Invoice.id == invoice_id)
    if user_id is not None:
        query = query.filter(models.Invoice.userId == user_id)
    db_invoice = query.first()
    if not db_invoice:
        return None
    
    # Update reminder status
    db_invoice.reminderSent = True
    db_invoice.reminderDate = datetime.utcnow().date()
    db_invoice.updatedAt = datetime.utcnow()
    
    db.commit()
    
    # TODO: Implement actual reminder sending logic (SendPulse integration)
    # For now, return success response
    return {
        "success": True,
        "message": "Promemoria inviato con successo",
        "sent_via": reminder_data.get("send_via", "email"),
        "sent_at": datetime.utcnow().isoformat()
    }

def get_overdue_invoices(db: Session, days_overdue: int = 7, include_tenant_info: bool = True, user_id: Optional[int] = None):
    """Get overdue invoices."""
    cutoff_date = datetime.utcnow().date() - timedelta(days=days_overdue)
    
    query = db.query(models.Invoice).filter(
        models.Invoice.isPaid == False,
        models.Invoice.dueDate < cutoff_date
    )
    if user_id is not None:
        query = query.filter(models.Invoice.userId == user_id)
    
    if include_tenant_info:
        query = query.join(models.Tenant)
    
    return query.order_by(models.Invoice.dueDate.asc()).all()

def generate_monthly_invoices(db: Session, data: dict):
    """Generate monthly invoices for all active leases."""
    month = data.get('month', datetime.utcnow().month)
    year = data.get('year', datetime.utcnow().year)
    include_utilities = data.get('include_utilities', True)
    send_notifications = data.get('send_notifications', False)
    
    # Get active leases
    active_leases = db.query(models.Lease).filter(
        models.Lease.endDate >= datetime.utcnow().date()
    ).all()
    
    generated_count = 0
    total_amount = 0
    
    for lease in active_leases:
        # Check if invoice already exists for this month/year
        existing_invoice = db.query(models.Invoice).filter(
            models.Invoice.leaseId == lease.id,
            models.Invoice.month == month,
            models.Invoice.year == year
        ).first()
        
        if existing_invoice:
            continue
        
        # Create invoice items
        rent_month_name = [
            "", "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
            "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
        ][month]
        
        items = [
            schemas.InvoiceItemCreate(
                invoiceId=0,
                description=f"Affitto {rent_month_name} {year}",
                amount=lease.monthlyRent,
                type="rent"
            )
        ]
        
        # Add utility costs and fixed costs if requested
        if include_utilities:
            items.extend(get_detailed_utility_and_fixed_items(db, lease.apartmentId, month, year, user_id=lease.userId))
        
        # Create invoice
        invoice_data = schemas.InvoiceCreate(
            leaseId=lease.id,
            tenantId=lease.tenantId,
            apartmentId=lease.apartmentId,
            invoiceNumber="",  # Will be auto-generated
            month=month,
            year=year,
            issueDate=datetime.utcnow().date(),
            dueDate=datetime.utcnow().date() + timedelta(days=15),
            notes=f"Fattura automatica per {rent_month_name} {year}",
            items=items
        )
        
        invoice = create_invoice(db, invoice_data, user_id=lease.userId)
        generated_count += 1
        total_amount += invoice.total
    
    return {
        "generated_count": generated_count,
        "total_amount": total_amount,
        "message": f"Fatture mensili generate con successo per {generated_count} contratti"
    }

def generate_invoice_from_lease(db: Session, data: dict):
    """Generate an invoice from a specific lease."""
    lease_id = data.get('lease_id')
    month = data.get('month', datetime.utcnow().month)
    year = data.get('year', datetime.utcnow().year)
    include_utilities = data.get('include_utilities', True)
    custom_items = data.get('custom_items', [])
    
    lease = db.query(models.Lease).filter(models.Lease.id == lease_id).first()
    if not lease:
        return {"error": "Lease not found"}
    
    # Create invoice items
    rent_month_name = [
        "", "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
    ][month]
    
    items = [
        schemas.InvoiceItemCreate(
            invoiceId=0,
            description=f"Affitto {rent_month_name} {year}",
            amount=lease.monthlyRent,
            type="rent"
        )
    ]
    
    # Add utility costs and fixed costs if requested
    if include_utilities:
        items.extend(get_detailed_utility_and_fixed_items(db, lease.apartmentId, month, year, user_id=lease.userId))
    
    # Add custom items
    for custom_item in custom_items:
        items.append(schemas.InvoiceItemCreate(
            invoiceId=0,
            description=custom_item.get('description', ''),
            amount=custom_item.get('amount', 0),
            type=custom_item.get('type', 'other')
        ))
    
    # Create invoice
    invoice_data = schemas.InvoiceCreate(
        leaseId=lease.id,
        tenantId=lease.tenantId,
        apartmentId=lease.apartmentId,
        invoiceNumber="",
        month=month,
        year=year,
        issueDate=datetime.utcnow().date(),
        dueDate=datetime.utcnow().date() + timedelta(days=15),
        notes=f"Fattura generata da contratto per {rent_month_name} {year}",
        items=items
    )
    
    invoice = create_invoice(db, invoice_data, user_id=lease.userId)
    
    return {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoiceNumber,
        "total": invoice.total,
        "message": "Fattura generata con successo"
    }

def get_invoice_statistics(db: Session, period: str = "this_month", user_id: Optional[int] = None):
    """Get invoice statistics and KPI."""
    today = datetime.utcnow().date()
    
    if period == "this_month":
        start_date = today.replace(day=1)
        end_date = today
    elif period == "last_month":
        if today.month == 1:
            start_date = today.replace(year=today.year-1, month=12, day=1)
        else:
            start_date = today.replace(month=today.month-1, day=1)
        end_date = start_date.replace(day=28) + timedelta(days=4)
        end_date = end_date.replace(day=1) - timedelta(days=1)
    elif period == "this_year":
        start_date = today.replace(month=1, day=1)
        end_date = today
    else:  # all
        start_date = date(2020, 1, 1)
        end_date = today
    
    # Get invoices for the period
    query = db.query(models.Invoice).filter(
        models.Invoice.issueDate >= start_date,
        models.Invoice.issueDate <= end_date
    )
    if user_id is not None:
        query = query.filter(models.Invoice.userId == user_id)
    invoices = query.all()
    
    total_invoiced = sum(inv.total for inv in invoices)
    total_paid = sum(inv.total for inv in invoices if inv.isPaid)
    total_unpaid = total_invoiced - total_paid
    
    # Count overdue invoices
    overdue_invoices = db.query(models.Invoice).filter(
        models.Invoice.isPaid == False,
        models.Invoice.dueDate < today
    ).count()
    
    # This month invoices
    this_month_invoices = db.query(models.Invoice).filter(
        models.Invoice.issueDate >= today.replace(day=1),
        models.Invoice.issueDate <= today
    ).count()
    
    return {
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "total_unpaid": total_unpaid,
        "overdue_invoices": overdue_invoices,
        "this_month_invoices": this_month_invoices,
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat()
    }

def generate_invoice_pdf(db: Session, invoice_id: int, include_logo: bool = True, 
                        include_qr_code: bool = True, include_payment_instructions: bool = True):
    """Generate PDF for an invoice."""
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        return None
    
    # TODO: Implement PDF generation logic
    # For now, return a placeholder response
    return {
        "invoice_id": invoice_id,
        "pdf_url": f"/static/invoices/{invoice.invoiceNumber}.pdf",
        "message": "PDF generato con successo"
    }

def send_bulk_reminders(db: Session, data: dict, user_id: Optional[int] = None):
    """Send reminders for multiple invoices."""
    invoice_ids = data.get('invoice_ids', [])
    send_via = data.get('send_via', 'email')
    template = data.get('template', 'default')
    custom_message = data.get('custom_message', '')
    
    results = []
    sent_count = 0
    failed_count = 0
    
    for invoice_id in invoice_ids:
        try:
            # Verify invoice belongs to user
            query = db.query(models.Invoice).filter(models.Invoice.id == invoice_id)
            if user_id is not None:
                query = query.filter(models.Invoice.userId == user_id)
            if not query.first():
                failed_count += 1
                continue
            
            reminder_data = {
                "send_via": send_via,
                "template": template,
                "message": custom_message
            }
            result = send_invoice_reminder(db, invoice_id, reminder_data, user_id=user_id)
            
            if result and result.get('success'):
                sent_count += 1
                results.append({
                    "invoice_id": invoice_id,
                    "success": True,
                    "message": "Promemoria inviato"
                })
            else:
                failed_count += 1
                results.append({
                    "invoice_id": invoice_id,
                    "success": False,
                    "message": "Errore nell'invio"
                })
        except Exception as e:
            failed_count += 1
            results.append({
                "invoice_id": invoice_id,
                "success": False,
                "message": str(e)
            })
    
    return {
        "sent_count": sent_count,
        "failed_count": failed_count,
        "results": results
    }

def generate_invoice_number(db: Session):
    """Generate a unique invoice number."""
    current_year = datetime.utcnow().year
    prefix = f"INV-{current_year}-"
    
    # Get the last invoice number for this year
    last_invoice = db.query(models.Invoice).filter(
        models.Invoice.invoiceNumber.like(f"{prefix}%")
    ).order_by(models.Invoice.invoiceNumber.desc()).first()
    
    if last_invoice:
        try:
            last_number = int(last_invoice.invoiceNumber.split('-')[-1])
            new_number = last_number + 1
        except (ValueError, IndexError):
            new_number = 1
    else:
        new_number = 1
    
    return f"{prefix}{new_number:03d}"

def get_lease_invoices(
    db: Session, 
    leaseId: int, 
    isPaid: Optional[bool] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    user_id: Optional[int] = None
):
    """Get invoices for a lease with optional filters."""
    query = db.query(models.Invoice).filter(
        models.Invoice.leaseId == leaseId
    )
    if user_id is not None:
        query = query.filter(models.Invoice.userId == user_id)
    
    if isPaid is not None:
        query = query.filter(models.Invoice.isPaid == isPaid)
    
    if year:
        query = query.filter(models.Invoice.year == year)
    
    if month:
        query = query.filter(models.Invoice.month == month)
    
    return query.order_by(models.Invoice.issueDate.desc()).all()

def calculate_utility_costs(db: Session, apartment_id: int, month: int, year: int):
    """Calculate utility costs for a specific month and year."""
    # This is kept for backward compatibility if needed, 
    # but get_detailed_utility_and_fixed_items is preferred now.
    apartment = db.query(models.Apartment).filter(models.Apartment.id == apartment_id).first()
    
    readings = db.query(models.UtilityReading).filter(
        models.UtilityReading.apartmentId == apartment_id,
        models.UtilityReading.readingDate >= date(year, month, 1),
        models.UtilityReading.readingDate <= date(year, month, 28) + timedelta(days=4)
    ).all()
    
    costs = {
        "electricity": 0.0,
        "water": 0.0,
        "gas": 0.0
    }
    
    is_apartment_8 = apartment and apartment.name == "Appartamento 8"
    
    if is_apartment_8:
        electricity_main = 0.0
        electricity_laundry = 0.0
        for reading in readings:
            if reading.type == "electricity":
                if reading.subtype == "laundry":
                    electricity_laundry += reading.totalCost
                else:
                    electricity_main += reading.totalCost
            elif reading.type in costs:
                costs[reading.type] += reading.totalCost
        costs["electricity"] = electricity_main
        if electricity_laundry > 0:
            costs["electricity_laundry"] = electricity_laundry
    else:
        for reading in readings:
            if reading.type in costs:
                costs[reading.type] += reading.totalCost
    return costs

def get_detailed_utility_and_fixed_items(db: Session, apartment_id: int, month: int, year: int, user_id: int) -> List[schemas.InvoiceItemCreate]:
    """Get detailed items for utilities (from previous month) and fixed costs."""
    # Utilities: fetch for previous month
    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year = year - 1
    
    readings = db.query(models.UtilityReading).filter(
        models.UtilityReading.apartmentId == apartment_id,
        models.UtilityReading.readingDate >= date(prev_year, prev_month, 1),
        models.UtilityReading.readingDate <= date(prev_year, prev_month, 28) + timedelta(days=4)
    ).all()
    
    items = []
    type_labels = {
        "electricity": "LUCE",
        "water": "ACQUA",
        "gas": "GAS"
    }
    
    for r in readings:
        label = type_labels.get(r.type, r.type.upper())
        if r.subtype == "laundry":
            label = "LUCE LAVANDERIA"
            
        unit = "kWh" if r.type == "electricity" else "m³"
        
        desc = f"{label} A {r.currentReading} P {r.previousReading} | {r.consumption} {unit} x {r.unitCost} €/{unit}"
        
        items.append(schemas.InvoiceItemCreate(
            invoiceId=0,
            description=desc,
            amount=r.totalCost,
            type=r.type
        ))
    
    # Fixed costs from defaults
    defaults = get_defaults(db, user_id=user_id)
    items.append(schemas.InvoiceItemCreate(
        invoiceId=0,
        description="TARI (N. Urbana)",
        amount=float(defaults.tari),
        type="tari"
    ))
    items.append(schemas.InvoiceItemCreate(
        invoiceId=0,
        description="Contatori",
        amount=float(defaults.meterFee),
        type="meter_fee"
    ))
    
    return items

def get_laundry_electricity_cost_for_month(db: Session, apartment_id: int, month: int, year: int):
    """Get laundry electricity cost for a specific apartment, month and year."""
    readings = db.query(models.UtilityReading).filter(
        models.UtilityReading.apartmentId == apartment_id,
        models.UtilityReading.type == "electricity",
        models.UtilityReading.subtype == "laundry",
        models.UtilityReading.readingDate >= date(year, month, 1),
        models.UtilityReading.readingDate <= date(year, month, 28) + timedelta(days=4)
    ).all()
    
    return sum(reading.totalCost for reading in readings)

def get_laundry_electricity_cost_for_apartment(db: Session, apartment_id: int, year: int):
    """Get total laundry electricity cost for a specific apartment and year."""
    readings = db.query(models.UtilityReading).filter(
        models.UtilityReading.apartmentId == apartment_id,
        models.UtilityReading.type == "electricity",
        models.UtilityReading.subtype == "laundry",
        func.extract('year', models.UtilityReading.readingDate) == year
    ).all()
    
    return sum(reading.totalCost for reading in readings)


# ----- ID Management Services -----

def get_next_available_id(db: Session, table_name: str, user_id: int) -> int:
    """Get the next available ID for a table, reusing deleted IDs if available."""
    # First, try to get a freed ID
    freed_id_record = db.query(models.FreeId).filter(
        models.FreeId.table_name == table_name
    ).first()

    if freed_id_record:
        # Use the freed ID
        freed_id = freed_id_record.freed_id
        db.delete(freed_id_record)
        db.commit()
        return freed_id
    else:
        # No freed ID available, get the next auto-increment value
        # This is a simplified approach - in production you'd want a more robust solution
        # For now, we'll use a simple approach that might have race conditions
        # but works for development
        return None  # Let the database handle auto-increment


def free_id_for_reuse(db: Session, table_name: str, freed_id: int):
    """Mark an ID as available for reuse when an entity is soft-deleted."""
    # Only free IDs that are not 1 (to avoid conflicts with system IDs)
    if freed_id > 1:
        free_id_record = models.FreeId(
            table_name=table_name,
            freed_id=freed_id
        )
        db.add(free_id_record)
        db.commit()


def soft_delete_entity(db: Session, model_class, entity_id: int, user_id: int):
    """Perform soft delete on an entity and free its ID for reuse."""
    entity = db.query(model_class).filter(
        model_class.id == entity_id,
        model_class.userId == user_id,
        model_class.deletedAt.is_(None)
    ).first()

    if not entity:
        return None

    # Soft delete
    entity.deletedAt = datetime.utcnow()
    db.commit()

    # Free the ID for reuse
    table_name = model_class.__tablename__
    free_id_for_reuse(db, table_name, entity_id)

    return entity


def create_entity_with_custom_id(db: Session, model_class, data: Dict[str, Any], user_id: int) -> Any:
    """Create an entity, potentially reusing a freed ID."""
    # Try to get a freed ID first
    freed_id_record = db.query(models.FreeId).filter(
        models.FreeId.table_name == model_class.__tablename__
    ).first()

    if freed_id_record:
        # Use the freed ID
        custom_id = freed_id_record.freed_id
        db.delete(freed_id_record)

        # Create entity with the specific ID
        data['id'] = custom_id
        data['userId'] = user_id
        entity = model_class(**data)
        db.add(entity)
        db.commit()
        db.refresh(entity)
        return entity
    else:
        # No freed ID, let database handle auto-increment
        data['userId'] = user_id
        entity = model_class(**data)
        db.add(entity)
        db.commit()
        db.refresh(entity)
        return entity


# ----- Enhanced CRUD Operations with Multi-tenancy -----

def get_entities_for_user(db: Session, model_class, user_id: int, skip: int = 0, limit: int = 100):
    """Get all entities for a specific user (excluding soft-deleted)."""
    return db.query(model_class).filter(
        model_class.userId == user_id,
        model_class.deletedAt.is_(None)
    ).offset(skip).limit(limit).all()


def get_entity_for_user(db: Session, model_class, entity_id: int, user_id: int):
    """Get a specific entity for a user (excluding soft-deleted)."""
    return db.query(model_class).filter(
        model_class.id == entity_id,
        model_class.userId == user_id,
        model_class.deletedAt.is_(None)
    ).first()


def update_entity_for_user(db: Session, model_class, entity_id: int, update_data: Dict[str, Any], user_id: int):
    """Update an entity for a specific user."""
    entity = db.query(model_class).filter(
        model_class.id == entity_id,
        model_class.userId == user_id,
        model_class.deletedAt.is_(None)
    ).first()

    if not entity:
        return None

    for key, value in update_data.items():
        if hasattr(entity, key):
            setattr(entity, key, value)

    entity.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(entity)
    return entity


def delete_entity_for_user(db: Session, model_class, entity_id: int, user_id: int):
    """Soft delete an entity for a specific user and free its ID."""
    return soft_delete_entity(db, model_class, entity_id, user_id)


# ----- Auto-Invoice Generation -----

import logging
logger = logging.getLogger(__name__)


def create_entry_invoice(db: Session, lease, user_id: int):
    """
    Genera automaticamente una fattura di ingresso (caparra) alla creazione del contratto.
    
    - 1 item: type="entry", amount=securityDeposit
    - dueDate = issueDate + 10 giorni
    - invoiceNumber con prefisso "CAP-"
    """
    if not lease.securityDeposit or lease.securityDeposit <= 0:
        logger.info(f"Lease {lease.id}: nessun securityDeposit, fattura ingresso non generata")
        return None

    # Recupera il nome dell'appartamento per la descrizione
    apartment = db.query(models.Apartment).filter(models.Apartment.id == lease.apartmentId).first()
    apt_name = apartment.name if apartment else f"Apt {lease.apartmentId}"

    issue_date = lease.startDate
    due_date = issue_date + timedelta(days=10)

    # Genera invoice number con prefisso CAP-
    timestamp = int(datetime.utcnow().timestamp() * 1000)
    invoice_number = f"CAP-{timestamp}-{lease.id}"

    # Crea la fattura
    db_invoice = models.Invoice(
        leaseId=lease.id,
        tenantId=lease.tenantId,
        apartmentId=lease.apartmentId,
        invoiceNumber=invoice_number,
        month=issue_date.month,
        year=issue_date.year,
        issueDate=issue_date,
        dueDate=due_date,
        subtotal=0.0,
        tax=0.0,
        total=lease.securityDeposit,
        notes="Fattura di ingresso - Caparra",
        userId=user_id
    )
    db.add(db_invoice)
    db.flush()

    # Crea l'item di caparra
    db_item = models.InvoiceItem(
        invoiceId=db_invoice.id,
        description=f"Caparra {apt_name}",
        amount=lease.securityDeposit,
        type="entry",
        userId=user_id
    )
    db.add(db_item)

    db.commit()
    db.refresh(db_invoice)

    logger.info(f"Fattura ingresso {invoice_number} generata per lease {lease.id}, importo {lease.securityDeposit}")
    return db_invoice


def check_and_generate_monthly_invoice(db: Session, apartment_id: int, user_id: int):
    """
    Controlla se tutte le utenze obbligatorie hanno una lettura successiva al baseline
    e, in caso affermativo, genera automaticamente la fattura mensile.
    
    Flusso:
    1. Trova il lease attivo per l'appartamento
    2. Verifica che il lease abbia baseline readings impostati
    3. Per ogni tipo obbligatorio (electricity, water, gas), cerca la prima lettura con id > baseline
    4. Se tutti presenti → genera fattura con affitto + utenze + costi fissi
    5. Aggiorna i baseline IDs nel lease con le letture appena usate
    
    Returns:
        Invoice object se generata, None altrimenti
    """
    # 1. Trova il lease attivo per l'appartamento
    today = date.today()
    lease = db.query(models.Lease).filter(
        models.Lease.apartmentId == apartment_id,
        models.Lease.userId == user_id,
        models.Lease.deletedAt.is_(None),
        models.Lease.startDate <= today,
        models.Lease.endDate > today
    ).first()

    if not lease:
        logger.debug(f"Nessun lease attivo per appartamento {apartment_id}")
        return None

    # 2. Verifica che il lease abbia baseline readings
    if not lease.electricityReadingId or not lease.waterReadingId or not lease.gasReadingId:
        logger.debug(f"Lease {lease.id}: baseline readings non impostati, skip")
        return None

    # 3. Per ogni tipo obbligatorio, cerca la prima lettura con id > baseline
    required_types = {
        "electricity": lease.electricityReadingId,
        "water": lease.waterReadingId,
        "gas": lease.gasReadingId,
    }

    next_readings = {}
    baseline_readings = {}

    for utype, baseline_id in required_types.items():
        # Recupera la lettura baseline
        baseline = db.query(models.UtilityReading).filter(
            models.UtilityReading.id == baseline_id
        ).first()
        if not baseline:
            logger.warning(f"Lease {lease.id}: baseline reading id={baseline_id} tipo {utype} non trovata")
            return None
        baseline_readings[utype] = baseline

        # Cerca la prima lettura successiva (stesso appartamento, stesso tipo, subtype principale)
        next_reading = db.query(models.UtilityReading).filter(
            models.UtilityReading.apartmentId == apartment_id,
            models.UtilityReading.type == utype,
            models.UtilityReading.id > baseline_id,
            models.UtilityReading.deletedAt.is_(None),
            # Escludi letture con subtype 'laundry' dalla ricerca electricity principale
            (models.UtilityReading.subtype.is_(None) | (models.UtilityReading.subtype != 'laundry')) if utype == 'electricity' else True
        ).order_by(models.UtilityReading.id.asc()).first()

        if not next_reading:
            logger.debug(f"Lease {lease.id}: nessuna lettura successiva per {utype} dopo baseline id={baseline_id}")
            return None

        next_readings[utype] = next_reading

    # Opzionale: lavanderia
    next_laundry = None
    baseline_laundry = None
    if lease.electricityLaundryReadingId:
        baseline_laundry = db.query(models.UtilityReading).filter(
            models.UtilityReading.id == lease.electricityLaundryReadingId
        ).first()

        if baseline_laundry:
            next_laundry = db.query(models.UtilityReading).filter(
                models.UtilityReading.apartmentId == apartment_id,
                models.UtilityReading.type == 'electricity',
                models.UtilityReading.subtype == 'laundry',
                models.UtilityReading.id > lease.electricityLaundryReadingId,
                models.UtilityReading.deletedAt.is_(None)
            ).order_by(models.UtilityReading.id.asc()).first()
            # La lavanderia è opzionale: se non c'è, procediamo comunque

    # 4. Tutte le utenze obbligatorie hanno una lettura successiva → genera fattura!

    # Determina mese/anno dalla lettura più recente tra le 3
    latest_reading = max(next_readings.values(), key=lambda r: r.readingDate)
    invoice_month = latest_reading.readingDate.month
    invoice_year = latest_reading.readingDate.year

    issue_date = date.today()
    due_date = issue_date + timedelta(days=15)

    # Genera invoice number
    invoice_number = generate_invoice_number(db)

    # Nomi mesi in italiano
    month_names = [
        "", "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
    ]

    # Recupera nome appartamento
    apartment = db.query(models.Apartment).filter(models.Apartment.id == apartment_id).first()
    apt_name = apartment.name if apartment else f"Apt {apartment_id}"

    # Costruisci gli items
    items_data = []

    # Item 1: Affitto
    items_data.append({
        "description": f"Affitto {month_names[invoice_month]} {invoice_year}",
        "amount": lease.monthlyRent,
        "type": "rent"
    })

    # Items 2-4: Utenze obbligatorie
    for utype in ["electricity", "water", "gas"]:
        baseline = baseline_readings[utype]
        current = next_readings[utype]

        consumption = current.currentReading - baseline.currentReading
        cost = current.totalCost if current.totalCost else consumption * current.unitCost

        type_labels = {
            "electricity": "Elettricità",
            "water": "Acqua",
            "gas": "Gas"
        }
        type_units = {
            "electricity": "kWh",
            "water": "m³",
            "gas": "m³"
        }

        label = type_labels.get(utype, utype)
        unit = type_units.get(utype, "")

        description = (
            f"{label}: lettura {baseline.currentReading:.1f} → {current.currentReading:.1f} "
            f"(consumo {consumption:.1f} {unit} × €{current.unitCost:.2f})"
        )

        items_data.append({
            "description": description,
            "amount": round(cost, 2),
            "type": utype
        })

    # Item opzionale: Lavanderia
    if next_laundry and baseline_laundry:
        consumption = next_laundry.currentReading - baseline_laundry.currentReading
        cost = next_laundry.totalCost if next_laundry.totalCost else consumption * next_laundry.unitCost

        description = (
            f"Elettricità Lavanderia: lettura {baseline_laundry.currentReading:.1f} → "
            f"{next_laundry.currentReading:.1f} "
            f"(consumo {consumption:.1f} kWh × €{next_laundry.unitCost:.2f})"
        )

        items_data.append({
            "description": description,
            "amount": round(cost, 2),
            "type": "electricity_laundry"
        })

    # Items costi fissi (TARI e Contatori) per l'utente
    defaults = get_defaults(db, user_id=user_id)
    items_data.append({
        "description": "TARI (quota mensile)",
        "amount": round(float(defaults.tari), 2),
        "type": "tari"
    })
    items_data.append({
        "description": "Contatori (quota mensile)",
        "amount": round(float(defaults.meterFee), 2),
        "type": "meter_fee"
    })

    # Calcola totali
    utility_types = ['electricity', 'water', 'gas', 'electricity_laundry']
    util_subtotal = sum(item["amount"] for item in items_data if item["type"] in utility_types)
    total = sum(item["amount"] for item in items_data)

    # Crea la fattura
    db_invoice = models.Invoice(
        leaseId=lease.id,
        tenantId=lease.tenantId,
        apartmentId=apartment_id,
        invoiceNumber=invoice_number,
        month=invoice_month,
        year=invoice_year,
        issueDate=issue_date,
        dueDate=due_date,
        subtotal=round(util_subtotal, 2),
        tax=0.0,
        total=round(total, 2),
        notes=f"Fattura generata automaticamente - {month_names[invoice_month]} {invoice_year}",
        userId=user_id
    )
    db.add(db_invoice)
    db.flush()

    # Crea gli items
    for item in items_data:
        db_item = models.InvoiceItem(
            invoiceId=db_invoice.id,
            description=item["description"],
            amount=item["amount"],
            type=item["type"],
            userId=user_id
        )
        db.add(db_item)

    # 5. AGGIORNA I BASELINE IDs nel lease
    lease.electricityReadingId = next_readings["electricity"].id
    lease.waterReadingId = next_readings["water"].id
    lease.gasReadingId = next_readings["gas"].id
    if next_laundry:
        lease.electricityLaundryReadingId = next_laundry.id
    lease.updatedAt = datetime.utcnow()

    db.commit()
    db.refresh(db_invoice)

    logger.info(
        f"Fattura mensile {invoice_number} generata per lease {lease.id}, "
        f"appartamento {apt_name}, mese {invoice_month}/{invoice_year}, "
        f"totale €{total:.2f}"
    )
    return db_invoice


def cascade_update_invoice_for_reading(db: Session, reading_id: int, user_id: int):
    """
    Quando una lettura utenze viene modificata, aggiorna a cascata la fattura che la utilizzava.
    
    Logica:
    1. La lettura modificata potrebbe essere il baseline corrente di un lease
       (cioè è stata la "lettura corrente" nell'ultima fattura generata)
    2. Trova il lease dove questa lettura è un baseline
    3. Trova la fattura più recente per quel lease
    4. Ricalcola l'item corrispondente e aggiorna i totali
    """
    # Carica la lettura aggiornata
    updated_reading = db.query(models.UtilityReading).filter(
        models.UtilityReading.id == reading_id
    ).first()
    if not updated_reading:
        return None

    apartment_id = updated_reading.apartmentId
    reading_type = updated_reading.type
    reading_subtype = updated_reading.subtype

    # Determina il tipo di item nella fattura
    if reading_type == "electricity" and reading_subtype == "laundry":
        invoice_item_type = "electricity_laundry"
        lease_field = "electricityLaundryReadingId"
    elif reading_type == "electricity":
        invoice_item_type = "electricity"
        lease_field = "electricityReadingId"
    elif reading_type == "water":
        invoice_item_type = "water"
        lease_field = "waterReadingId"
    elif reading_type == "gas":
        invoice_item_type = "gas"
        lease_field = "gasReadingId"
    else:
        return None

    # Cerca il lease dove questa lettura è il baseline corrente
    lease = db.query(models.Lease).filter(
        models.Lease.userId == user_id,
        models.Lease.deletedAt.is_(None),
        getattr(models.Lease, lease_field) == reading_id
    ).first()

    if not lease:
        logger.debug(f"Lettura {reading_id}: non è baseline di nessun lease, skip cascade invoice")
        return None

    # Trova la lettura precedente (usata come baseline nella fattura che ha generato questa come "current")
    # La lettura precedente è quella immediatamente prima di questa per lo stesso appartamento e tipo
    prev_query = db.query(models.UtilityReading).filter(
        models.UtilityReading.apartmentId == apartment_id,
        models.UtilityReading.type == reading_type,
        models.UtilityReading.id < reading_id,
        models.UtilityReading.deletedAt.is_(None)
    )
    if reading_subtype:
        prev_query = prev_query.filter(models.UtilityReading.subtype == reading_subtype)
    else:
        prev_query = prev_query.filter(
            (models.UtilityReading.subtype.is_(None)) | (models.UtilityReading.subtype != 'laundry')
        )
    
    prev_reading = prev_query.order_by(models.UtilityReading.id.desc()).first()

    if not prev_reading:
        logger.warning(f"Lettura {reading_id}: nessuna lettura precedente trovata, impossibile ricalcolare")
        return None

    # Ricalcola il consumo e il costo
    consumption = updated_reading.currentReading - prev_reading.currentReading
    cost = round(consumption * updated_reading.unitCost, 2)

    # Trova la fattura più recente per questo lease che contiene un item di questo tipo
    recent_invoice = db.query(models.Invoice).filter(
        models.Invoice.leaseId == lease.id,
        models.Invoice.deletedAt.is_(None),
        models.Invoice.items.any(models.InvoiceItem.type == invoice_item_type)
    ).order_by(models.Invoice.id.desc()).first()

    if not recent_invoice:
        logger.debug(f"Lettura {reading_id}: nessuna fattura trovata con item tipo {invoice_item_type}")
        return None

    # Aggiorna l'item corrispondente
    type_labels = {
        "electricity": "Elettricità",
        "water": "Acqua",
        "gas": "Gas",
        "electricity_laundry": "Elettricità Lavanderia"
    }
    type_units = {
        "electricity": "kWh",
        "water": "m³",
        "gas": "m³",
        "electricity_laundry": "kWh"
    }
    label = type_labels.get(invoice_item_type, invoice_item_type)
    unit = type_units.get(invoice_item_type, "")

    new_description = (
        f"{label}: lettura {prev_reading.currentReading:.1f} → {updated_reading.currentReading:.1f} "
        f"(consumo {consumption:.1f} {unit} × €{updated_reading.unitCost:.2f})"
    )

    item_updated = False
    for item in recent_invoice.items:
        if item.type == invoice_item_type:
            item.amount = cost
            item.description = new_description
            item.updatedAt = datetime.utcnow()
            item_updated = True
            break

    if not item_updated:
        logger.warning(f"Fattura {recent_invoice.id}: item tipo {invoice_item_type} non trovato")
        return None

    # Ricalcola i totali della fattura
    utility_types = ['electricity', 'water', 'gas', 'electricity_laundry']
    util_subtotal = sum(
        (i.amount or 0.0) for i in recent_invoice.items if i.type in utility_types
    )
    total = sum((i.amount or 0.0) for i in recent_invoice.items)

    recent_invoice.subtotal = round(util_subtotal, 2)
    recent_invoice.total = round(total, 2)
    recent_invoice.updatedAt = datetime.utcnow()

    db.commit()
    db.refresh(recent_invoice)

    logger.info(
        f"Fattura {recent_invoice.invoiceNumber} aggiornata a cascata: "
        f"item {invoice_item_type} → €{cost:.2f}, totale → €{recent_invoice.total:.2f}"
    )
    return recent_invoice