from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, Float, Date, DateTime, JSON, Enum, Numeric, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import time
from datetime import datetime, date

from app.database import Base

# Tabella per gestire il riutilizzo degli ID
class FreeId(Base):
    __tablename__ = "free_ids"

    table_name = Column(String, primary_key=True, index=True)  # Nome della tabella
    freed_id = Column(Integer, primary_key=True)  # ID liberato
    freed_at = Column(DateTime, default=datetime.utcnow)

    def __str__(self):
        return f"FreeId(table={self.table_name}, id={self.freed_id})"

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
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashedPassword = Column(String)
    firstName = Column(String)
    lastName = Column(String)
    role = Column(String)
    isActive = Column(Boolean, default=True)
    lastLogin = Column(DateTime, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deletedAt = Column(DateTime, nullable=True)  # Per soft delete
    
    # Relationship con RefreshToken
    refreshTokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    # Relationship con PasswordResetToken
    reset_tokens = relationship("PasswordResetToken", back_populates="user")

    # Relationship con Apartments (nuova per multi-tenancy)
    apartments = relationship("Apartment", back_populates="user", cascade="all, delete-orphan")

    # Relationship con MaintenanceRecords (nuova per multi-tenancy)
    maintenance_records = relationship("MaintenanceRecord", back_populates="user", cascade="all, delete-orphan")

    # Relationship con Tenants (nuova per multi-tenancy)
    tenants = relationship("Tenant", back_populates="user", cascade="all, delete-orphan")

    # Relationship con Leases (nuova per multi-tenancy)
    leases = relationship("Lease", back_populates="user", cascade="all, delete-orphan")

    # Relationship con Invoices (nuova per multi-tenancy)
    invoices = relationship("Invoice", back_populates="user", cascade="all, delete-orphan")

    # Relationship con UtilityReadings (nuova per multi-tenancy)
    utility_readings = relationship("UtilityReading", back_populates="user", cascade="all, delete-orphan")

    # Relationship con LeaseDocuments (nuova per multi-tenancy)
    lease_documents = relationship("LeaseDocument", back_populates="user", cascade="all, delete-orphan")

    # Relationship con LeasePayments (nuova per multi-tenancy)
    lease_payments = relationship("LeasePayment", back_populates="user", cascade="all, delete-orphan")

    # Relationship con InvoiceItems (nuova per multi-tenancy)
    invoice_items = relationship("InvoiceItem", back_populates="user", cascade="all, delete-orphan")

    # Relationship con PaymentRecords (nuova per multi-tenancy)
    payment_records = relationship("PaymentRecord", back_populates="user", cascade="all, delete-orphan")

    # Relationship con BillingDefaults (nuova per multi-tenancy)
    billing_defaults = relationship("BillingDefaults", back_populates="user", cascade="all, delete-orphan")
    
    def __str__(self):
        return f"User(id={self.id}, username={self.username}, email={self.email}, role={self.role}, active={self.isActive})"
    
    def __repr__(self):
        return self.__str__()

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    username = Column(String, ForeignKey("users.username"))
    expires = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime, nullable=True)
    
    # Relationship con User
    user = relationship("User", back_populates="refreshTokens")
    
    def __str__(self):
        return f"RefreshToken(id={self.id}, username={self.username}, expires={self.expires}, revoked={self.is_revoked})"
    
    def __repr__(self):
        return self.__str__()

class Apartment(Base):
    __tablename__ = "apartments"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("users.id"), nullable=False)  # Multi-tenancy
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
    notes = Column(Text, nullable=True)
    utilityMetersInfo = Column(JSON, nullable=True)
    amenities = Column(JSON, nullable=True)  # Array di stringhe
    images = Column(JSON, nullable=True)  # Array di URL di immagini
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deletedAt = Column(DateTime, nullable=True)  # Per soft delete

    # Relazione con User (nuova per multi-tenancy)
    user = relationship("User", back_populates="apartments")

    # Relazioni
    utilityReadings = relationship("UtilityReading", back_populates="apartment", cascade="all, delete-orphan")
    maintenanceRecords = relationship("MaintenanceRecord", back_populates="apartment", cascade="all, delete-orphan")
    leases = relationship("Lease", back_populates="apartment")
    invoices = relationship("Invoice", back_populates="apartment")

class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("users.id"), nullable=False)  # Multi-tenancy
    apartmentId = Column(Integer, ForeignKey("apartments.id"))
    type = Column(String)  # 'repair', 'inspection', 'upgrade', 'cleaning'
    description = Column(Text)
    cost = Column(Float)
    date = Column(Date)
    completedBy = Column(String)
    notes = Column(Text, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deletedAt = Column(DateTime, nullable=True)  # Per soft delete

    # Relazione con User (nuova per multi-tenancy)
    user = relationship("User", back_populates="maintenance_records")

    # Relazioni
    apartment = relationship("Apartment", back_populates="maintenanceRecords")

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("users.id"), nullable=False)  # Multi-tenancy
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
    deletedAt = Column(DateTime, nullable=True)  # Per soft delete

    # Relazione con User (nuova per multi-tenancy)
    user = relationship("User", back_populates="tenants")

    # Relazioni
    leases = relationship("Lease", back_populates="tenant")
    invoices = relationship("Invoice", back_populates="tenant")

    @property
    def documentFrontImageUrl(self):
        """Ritorna l'URL completo con parametro anti-cache se esiste un'immagine."""
        if self.documentFrontImage:
            timestamp = int(time.time())
            return f"{self.documentFrontImage}?t={timestamp}"
        return None
    
    @property
    def documentBackImageUrl(self):
        """Ritorna l'URL completo con parametro anti-cache se esiste un'immagine."""
        if self.documentBackImage:
            timestamp = int(time.time())
            return f"{self.documentBackImage}?t={timestamp}"
        return None

class Lease(Base):
    __tablename__ = "leases"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("users.id"), nullable=False)  # Multi-tenancy
    tenantId = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    apartmentId = Column(Integer, ForeignKey("apartments.id"), nullable=False)
    startDate = Column(Date)
    endDate = Column(Date)
    monthlyRent = Column(Float)
    securityDeposit = Column(Float)
    paymentDueDay = Column(Integer)
    termsAndConditions = Column(Text)
    specialClauses = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deletedAt = Column(DateTime, nullable=True)  # Per soft delete

    # Relazione con User (nuova per multi-tenancy)
    user = relationship("User", back_populates="leases")

    # Relazioni
    tenant = relationship("Tenant", back_populates="leases")
    apartment = relationship("Apartment", back_populates="leases")
    documents = relationship("LeaseDocument", back_populates="lease")
    payments = relationship("LeasePayment", back_populates="lease")
    invoices = relationship("Invoice", back_populates="lease")
    
    @property
    def isActive(self):
        """Determina se il contratto è attivo. È attivo fino alle 23:59 del giorno precedente alla data di fine."""
        return date.today() < self.endDate if self.endDate else True

    @property
    def status(self):
        """Restituisce lo stato del contratto come stringa ('active' o 'terminated')."""
        return "active" if self.isActive else "terminated"

class LeaseDocument(Base):
    __tablename__ = "lease_documents"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("users.id"), nullable=False)  # Multi-tenancy
    leaseId = Column(Integer, ForeignKey("leases.id"))
    name = Column(String)
    type = Column(String)
    url = Column(String)
    uploadDate = Column(Date)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deletedAt = Column(DateTime, nullable=True)  # Per soft delete

    # Relazione con User (nuova per multi-tenancy)
    user = relationship("User", back_populates="lease_documents")

    # Relazioni
    lease = relationship("Lease", back_populates="documents")

class LeasePayment(Base):
    __tablename__ = "lease_payments"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("users.id"), nullable=False)  # Multi-tenancy
    leaseId = Column(Integer, ForeignKey("leases.id"))
    amount = Column(Float)
    paymentDate = Column(Date)
    paymentType = Column(String)
    reference = Column(String)
    notes = Column(Text, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deletedAt = Column(DateTime, nullable=True)  # Per soft delete

    # Relazione con User (nuova per multi-tenancy)
    user = relationship("User", back_populates="lease_payments")

    # Relazioni
    lease = relationship("Lease", back_populates="payments")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("users.id"), nullable=False)  # Multi-tenancy
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
    deletedAt = Column(DateTime, nullable=True)  # Per soft delete

    # Relazione con User (nuova per multi-tenancy)
    user = relationship("User", back_populates="invoices")

    # Relazioni
    lease = relationship("Lease", back_populates="invoices")
    tenant = relationship("Tenant", back_populates="invoices")
    apartment = relationship("Apartment", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice")
    payments = relationship("PaymentRecord", back_populates="invoice")

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("users.id"), nullable=False)  # Multi-tenancy
    invoiceId = Column(Integer, ForeignKey("invoices.id"))
    description = Column(String)
    amount = Column(Float)
    type = Column(String)  # 'rent', 'electricity', 'water', 'gas', 'maintenance', 'other'
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deletedAt = Column(DateTime, nullable=True)  # Per soft delete

    # Relazione con User (nuova per multi-tenancy)
    user = relationship("User", back_populates="invoice_items")

    # Relazioni
    invoice = relationship("Invoice", back_populates="items")

class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("users.id"), nullable=False)  # Multi-tenancy
    invoiceId = Column(Integer, ForeignKey("invoices.id"))
    amount = Column(Float)
    paymentDate = Column(Date)
    paymentMethod = Column(String)  # 'cash', 'bankTransfer', 'creditCard', 'check'
    reference = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deletedAt = Column(DateTime, nullable=True)  # Per soft delete

    # Relazione con User (nuova per multi-tenancy)
    user = relationship("User", back_populates="payment_records")

    # Relazioni
    invoice = relationship("Invoice", back_populates="payments")

class UtilityReading(Base):
    __tablename__ = "utility_readings"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("users.id"), nullable=False)  # Multi-tenancy

    # Relazione con Apartment
    apartmentId = Column(Integer, ForeignKey("apartments.id"), nullable=False)
    apartment = relationship("Apartment", back_populates="utilityReadings")

    # Tipologia di lettura (electricity, water, gas)
    type = Column(String, nullable=False)

    # Sottotipo per letture speciali (es. 'main', 'laundry' per elettricità)
    subtype = Column(String, nullable=True)

    # Flag per identificare letture speciali
    isSpecialReading = Column(Boolean, default=False)

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

    # Timestamp e soft delete
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deletedAt = Column(DateTime, nullable=True)  # Per soft delete

    # Relazione con User (nuova per multi-tenancy)
    user = relationship("User", back_populates="utility_readings")

    # Altri campi opzionali per consumi/costi specifici
    electricityConsumption = Column(Float, nullable=True)
    waterConsumption = Column(Float, nullable=True)
    gasConsumption = Column(Float, nullable=True)
    electricityCost = Column(Float, nullable=True)
    waterCost = Column(Float, nullable=True)
    gasCost = Column(Float, nullable=True)

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    expires = Column(DateTime)
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)

    # Relazioni
    user = relationship("User", back_populates="reset_tokens")


class BillingDefaults(Base):
    __tablename__ = "billing_defaults"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("users.id"), nullable=False)  # Multi-tenancy
    # Valori globali
    tari = Column(Numeric(10, 2), nullable=False, default=15.00)
    meterFee = Column(Numeric(10, 2), nullable=False, default=3.00)

    # Costi unitari per utilities
    unitCostElectricity = Column(Numeric(10, 4), nullable=False, default=0.75)
    unitCostWater = Column(Numeric(10, 4), nullable=False, default=3.40)
    unitCostGas = Column(Numeric(10, 4), nullable=False, default=4.45)

    # Audit
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updatedBy = Column(BigInteger, nullable=True)
    deletedAt = Column(DateTime, nullable=True)  # Per soft delete

    # Relazione con User (nuova per multi-tenancy)
    user = relationship("User", back_populates="billing_defaults")