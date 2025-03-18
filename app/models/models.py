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
    bankTransfer = "bank transfer"
    creditCard = "credit card"
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
    squareMeters = Column(Float)
    rooms = Column(Integer)
    bathrooms = Column(Integer)
    hasBalcony = Column(Boolean, default=False)
    hasParking = Column(Boolean, default=False)
    isFurnished = Column(Boolean, default=False)
    monthlyRent = Column(Float)
    status = Column(String, default="available")
    isAvailable = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    utilityMetersInfo = Column(JSON, nullable=True)
    amenities = Column(JSON, nullable=True)  # Array di stringhe
    images = Column(JSON, nullable=True)  # Array di URL di immagini
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    utilityReadings = relationship("UtilityReading", back_populates="apartment", cascade="all, delete-orphan")
    maintenanceRecords = relationship("MaintenanceRecord", back_populates="apartment", cascade="all, delete-orphan")
    leases = relationship("Lease", back_populates="apartment")
    invoices = relationship("Invoice", back_populates="apartment")

class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id = Column(Integer, primary_key=True, index=True)
    apartmentId = Column(Integer, ForeignKey("apartments.id"))
    type = Column(String)  # 'repair', 'inspection', 'upgrade', 'cleaning'
    description = Column(Text)
    cost = Column(Float)
    date = Column(Date)
    completedBy = Column(String)
    notes = Column(Text, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    apartment = relationship("Apartment", back_populates="maintenanceRecords")

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    firstName = Column(String)
    lastName = Column(String)
    email = Column(String, nullable=True)
    phone = Column(String)
    documentType = Column(String)
    documentNumber = Column(String)
    documentExpiryDate = Column(Date)
    documentFrontImage = Column(String, nullable=True)
    documentBackImage = Column(String, nullable=True)
    address = Column(String, nullable=True)
    communicationPreferences = Column(JSON)  # { email: true, sms: true, whatsapp: true }
    notes = Column(Text, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    leases = relationship("Lease", back_populates="tenant")
    invoices = relationship("Invoice", back_populates="tenant")

class Lease(Base):
    __tablename__ = "leases"

    id = Column(Integer, primary_key=True, index=True)
    tenantId = Column(Integer, ForeignKey("tenants.id"))
    apartmentId = Column(Integer, ForeignKey("apartments.id"))
    startDate = Column(Date)
    endDate = Column(Date)
    monthlyRent = Column(Float)
    securityDeposit = Column(Float)
    isActive = Column(Boolean, default=True)
    paymentDueDay = Column(Integer)
    termsAndConditions = Column(Text)
    specialClauses = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    tenant = relationship("Tenant", back_populates="leases")
    apartment = relationship("Apartment", back_populates="leases")
    documents = relationship("LeaseDocument", back_populates="lease")
    payments = relationship("LeasePayment", back_populates="lease")
    invoices = relationship("Invoice", back_populates="lease")

class LeaseDocument(Base):
    __tablename__ = "lease_documents"

    id = Column(Integer, primary_key=True, index=True)
    leaseId = Column(Integer, ForeignKey("leases.id"))
    name = Column(String)
    type = Column(String)
    url = Column(String)
    uploadDate = Column(Date)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    lease = relationship("Lease", back_populates="documents")

class LeasePayment(Base):
    __tablename__ = "lease_payments"

    id = Column(Integer, primary_key=True, index=True)
    leaseId = Column(Integer, ForeignKey("leases.id"))
    amount = Column(Float)
    paymentDate = Column(Date)
    paymentType = Column(String)
    reference = Column(String)
    notes = Column(Text, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    lease = relationship("Lease", back_populates="payments")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    leaseId = Column(Integer, ForeignKey("leases.id"))
    tenantId = Column(Integer, ForeignKey("tenants.id"))
    apartmentId = Column(Integer, ForeignKey("apartments.id"))
    invoiceNumber = Column(String, index=True)
    month = Column(Integer)
    year = Column(Integer)
    issueDate = Column(Date)
    dueDate = Column(Date)
    subtotal = Column(Float)
    tax = Column(Float)
    total = Column(Float)
    isPaid = Column(Boolean, default=False)
    paymentDate = Column(Date, nullable=True)
    paymentMethod = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    reminderSent = Column(Boolean, default=False)
    reminderDate = Column(Date, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    lease = relationship("Lease", back_populates="invoices")
    tenant = relationship("Tenant", back_populates="invoices")
    apartment = relationship("Apartment", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice")
    payments = relationship("PaymentRecord", back_populates="invoice")

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoiceId = Column(Integer, ForeignKey("invoices.id"))
    description = Column(String)
    amount = Column(Float)
    type = Column(String)  # 'rent', 'electricity', 'water', 'gas', 'maintenance', 'other'
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    invoice = relationship("Invoice", back_populates="items")

class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id = Column(Integer, primary_key=True, index=True)
    invoiceId = Column(Integer, ForeignKey("invoices.id"))
    amount = Column(Float)
    paymentDate = Column(Date)
    paymentMethod = Column(String)  # 'cash', 'bankTransfer', 'creditCard', 'check'
    reference = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    invoice = relationship("Invoice", back_populates="payments")

class UtilityReading(Base):
    __tablename__ = "utility_readings"

    id = Column(Integer, primary_key=True, index=True)

    # Relazione con Apartment
    apartmentId = Column(Integer, ForeignKey("apartments.id"), nullable=False)
    apartment = relationship("Apartment", back_populates="utilityReadings")

    # Tipologia di lettura (electricity, water, gas)
    type = Column(String, nullable=False)

    # Date e campi di consumo
    readingDate = Column(Date, nullable=False)
    previousReading = Column(Float, default=0.0)
    currentReading = Column(Float, default=0.0)
    consumption = Column(Float, default=0.0)
    unitCost = Column(Float, default=0.0)
    totalCost = Column(Float, default=0.0)

    # Stato del pagamento
    isPaid = Column(Boolean, default=False)
    paidDate = Column(Date, nullable=True)

    # Eventuali note
    notes = Column(Text, nullable=True)

    # Altri campi opzionali per consumi/costi specifici
    electricityConsumption = Column(Float, nullable=True)
    waterConsumption = Column(Float, nullable=True)
    gasConsumption = Column(Float, nullable=True)
    electricityCost = Column(Float, nullable=True)
    waterCost = Column(Float, nullable=True)
    gasCost = Column(Float, nullable=True)

    # Timestamp
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)