from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, Float, Date, DateTime, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from datetime import datetime

from app.database import Base

# Enumerazioni per i tipi
class MaintenanceType(str, enum.Enum):
    repair = "repair"
    inspection = "inspection"
    upgrade = "upgrade"
    cleaning = "cleaning"

class ApartmentStatus(str, enum.Enum):
    available = "available"
    occupied = "occupied"
    maintenance = "maintenance"

class UtilityType(str, enum.Enum):
    electricity = "electricity"
    water = "water"
    gas = "gas"

class PaymentMethod(str, enum.Enum):
    cash = "cash"
    bank_transfer = "bank_transfer"
    credit_card = "credit_card"
    check = "check"

class InvoiceItemType(str, enum.Enum):
    rent = "rent"
    electricity = "electricity" 
    water = "water"
    gas = "gas"
    maintenance = "maintenance"
    other = "other"

class UserRole(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    staff = "staff"

# Modelli delle tabelle
class Apartment(Base):
    __tablename__ = "apartments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    floor = Column(Integer)
    square_meters = Column(Float)
    rooms = Column(Integer)
    bathrooms = Column(Integer)
    has_balcony = Column(Boolean, default=False)
    has_parking = Column(Boolean, default=False)
    is_furnished = Column(Boolean, default=False)
    monthly_rent = Column(Float)
    status = Column(String, default="available")
    is_available = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    utility_meters_info = Column(JSON, nullable=True)
    amenities = Column(JSON, nullable=True)  # Array di stringhe
    images = Column(JSON, nullable=True)  # Array di URL di immagini
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    utility_readings = relationship("UtilityReading", back_populates="apartment")
    maintenance_records = relationship("MaintenanceRecord", back_populates="apartment")
    leases = relationship("Lease", back_populates="apartment")
    invoices = relationship("Invoice", back_populates="apartment")

class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id = Column(Integer, primary_key=True, index=True)
    apartment_id = Column(Integer, ForeignKey("apartments.id"))
    type = Column(String)  # 'repair', 'inspection', 'upgrade', 'cleaning'
    description = Column(Text)
    cost = Column(Float)
    date = Column(Date)
    completed_by = Column(String)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    apartment = relationship("Apartment", back_populates="maintenance_records")

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, nullable=True)
    phone = Column(String)
    document_type = Column(String)
    document_number = Column(String)
    document_expiry_date = Column(Date)
    document_front_image = Column(String, nullable=True)
    document_back_image = Column(String, nullable=True)
    address = Column(String, nullable=True)
    communication_preferences = Column(JSON)  # { email: true, sms: true, whatsapp: true }
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    leases = relationship("Lease", back_populates="tenant")
    invoices = relationship("Invoice", back_populates="tenant")

class Lease(Base):
    __tablename__ = "leases"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    apartment_id = Column(Integer, ForeignKey("apartments.id"))
    start_date = Column(Date)
    end_date = Column(Date)
    monthly_rent = Column(Float)
    security_deposit = Column(Float)
    is_active = Column(Boolean, default=True)
    payment_due_day = Column(Integer)
    terms_and_conditions = Column(Text)
    special_clauses = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    tenant = relationship("Tenant", back_populates="leases")
    apartment = relationship("Apartment", back_populates="leases")
    documents = relationship("LeaseDocument", back_populates="lease")
    payments = relationship("LeasePayment", back_populates="lease")
    invoices = relationship("Invoice", back_populates="lease")

class LeaseDocument(Base):
    __tablename__ = "lease_documents"

    id = Column(Integer, primary_key=True, index=True)
    lease_id = Column(Integer, ForeignKey("leases.id"))
    name = Column(String)
    type = Column(String)
    url = Column(String)
    upload_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    lease = relationship("Lease", back_populates="documents")

class LeasePayment(Base):
    __tablename__ = "lease_payments"

    id = Column(Integer, primary_key=True, index=True)
    lease_id = Column(Integer, ForeignKey("leases.id"))
    amount = Column(Float)
    payment_date = Column(Date)
    payment_type = Column(String)
    reference = Column(String)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    lease = relationship("Lease", back_populates="payments")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    lease_id = Column(Integer, ForeignKey("leases.id"))
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    apartment_id = Column(Integer, ForeignKey("apartments.id"))
    invoice_number = Column(String, index=True)
    month = Column(Integer)
    year = Column(Integer)
    issue_date = Column(Date)
    due_date = Co