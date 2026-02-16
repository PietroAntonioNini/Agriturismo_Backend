from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date
from pydantic import BaseModel, EmailStr, validator, Field, field_validator

# Base model that converts camelCase to snake_case and vice versa
class CamelCaseModel(BaseModel):
    class Config:
        populate_by_name = True
        alias_generator = lambda s: ''.join(word.capitalize() if i else word for i, word in enumerate(s.split('_')))
        from_attributes = True
        validate_assignment = True
        arbitrary_types_allowed = True
        # orm_mode è deprecato, ma mantenuto per retrocompatibilità
        orm_mode = True
        
        @classmethod
        def get_properties(cls):
            return [prop for prop in dir(cls) if isinstance(getattr(cls, prop), property)]

# ------------------ SCHEMA UTILITY READING ------------------
class UtilityReadingBase(CamelCaseModel):
    apartmentId: int
    type: str
    readingDate: date
    previousReading: float
    currentReading: float
    consumption: float
    unitCost: float
    totalCost: float
    isPaid: bool = False
    notes: Optional[str] = None
    subtype: Optional[str] = None
    isSpecialReading: Optional[bool] = None
    electricityConsumption: Optional[float] = None
    waterConsumption: Optional[float] = None
    gasConsumption: Optional[float] = None
    electricityCost: Optional[float] = None
    waterCost: Optional[float] = None
    gasCost: Optional[float] = None

class UtilityReadingCreate(UtilityReadingBase):
    pass

class UtilityReading(UtilityReadingBase):
    id: int
    paidDate: Optional[date] = None
    createdAt: datetime
    updatedAt: datetime

# ------------------ SCHEMA MAINTENANCE RECORD ------------------
class MaintenanceRecordBase(CamelCaseModel):
    apartmentId: int
    type: str
    description: str
    cost: float
    date: date
    completedBy: str
    notes: Optional[str] = None

class MaintenanceRecordCreate(MaintenanceRecordBase):
    pass

class MaintenanceRecord(MaintenanceRecordBase):
    id: int
    createdAt: datetime
    updatedAt: datetime

# ------------------ SCHEMA APARTMENT ------------------
class ApartmentBase(CamelCaseModel):
    name: str
    description: Optional[str] = None
    floor: int
    squareMeters: float
    rooms: int
    bathrooms: int
    hasBalcony: bool = False
    hasParking: bool = False
    isFurnished: bool = False
    monthlyRent: float
    status: str
    notes: Optional[str] = None
    utilityMetersInfo: Optional[Dict[str, str]] = None
    amenities: Optional[List[str]] = None
    images: Optional[List[str]] = None

class ApartmentCreate(ApartmentBase):
    pass

class Apartment(ApartmentBase):
    id: int
    createdAt: datetime
    updatedAt: datetime
    utilityReadings: Optional[List[UtilityReading]] = []
    maintenanceRecords: Optional[List[MaintenanceRecord]] = []

# ------------------ SCHEMA TENANT ------------------
class CommunicationPreferences(CamelCaseModel):
    email: bool = True
    sms: bool = True
    whatsapp: bool = False

class TenantBase(CamelCaseModel):
    firstName: str
    lastName: str
    email: Optional[str] = None
    phone: str
    documentType: str
    documentNumber: str
    documentExpiryDate: date
    documentFrontImage: Optional[str] = None
    documentBackImage: Optional[str] = None
    address: Optional[str] = None
    communicationPreferences: CommunicationPreferences
    notes: Optional[str] = None
    
    @validator('documentExpiryDate', pre=True)
    def parse_date(cls, value):
        if isinstance(value, str):
            if 'T' in value:
                value = value.split('T')[0]
            return datetime.strptime(value, '%Y-%m-%d').date()
        return value

class TenantCreate(TenantBase):
    pass

class Tenant(TenantBase):
    id: int
    createdAt: datetime
    updatedAt: datetime

# ------------------ SCHEMA TENANT DOCUMENT ------------------

class DocumentResponse(CamelCaseModel):
    success: bool
    imageUrl: Optional[str] = None
    detail: Optional[str] = None
    timestamp: Optional[int] = None

# ------------------ SCHEMA LEASE DOCUMENT ------------------
class LeaseDocumentBase(CamelCaseModel):
    leaseId: int
    name: str
    type: str
    url: str
    uploadDate: date

class LeaseDocumentCreate(LeaseDocumentBase):
    pass

class LeaseDocument(LeaseDocumentBase):
    id: int
    createdAt: datetime
    updatedAt: datetime

# ------------------ SCHEMA LEASE PAYMENT ------------------
class LeasePaymentBase(CamelCaseModel):
    leaseId: int
    amount: float
    paymentDate: date
    paymentType: str
    reference: str
    notes: Optional[str] = None

class LeasePaymentCreate(LeasePaymentBase):
    pass

class LeasePayment(LeasePaymentBase):
    id: int
    createdAt: datetime
    updatedAt: datetime

# ------------------ SCHEMA LEASE ------------------
class LeaseBase(CamelCaseModel):
    tenantId: int
    apartmentId: int
    startDate: date
    endDate: date
    monthlyRent: float
    securityDeposit: float
    paymentDueDay: int
    termsAndConditions: str
    specialClauses: Optional[str] = None
    notes: Optional[str] = None

    @field_validator('startDate', 'endDate', mode='before')
    @classmethod
    def parse_date(cls, value):
        if isinstance(value, str):
            # Handles ISO format datetime strings like "2023-01-01T00:00:00.000Z"
            # by parsing them and taking only the date part.
            if 'T' in value:
                return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
        if isinstance(value, datetime):
            return value.date()
        # For values that are already date objects or 'YYYY-MM-DD' strings, Pydantic will handle them.
        return value

# Schema annidato per le letture iniziali (baseline)
class InitialReadings(CamelCaseModel):
    # Opzione 1: ID di letture esistenti
    electricityReadingId: Optional[int] = None
    waterReadingId: Optional[int] = None
    gasReadingId: Optional[int] = None
    electricityLaundryReadingId: Optional[int] = None
    
    # Opzione 2: Valori crudi (per nuovi appartamenti senza storico)
    electricityValue: Optional[float] = None
    waterValue: Optional[float] = None
    gasValue: Optional[float] = None
    electricityLaundryValue: Optional[float] = None

class LeaseCreate(LeaseBase):
    initialReadings: Optional[InitialReadings] = None

class Lease(LeaseBase):
    id: int
    createdAt: datetime
    updatedAt: datetime
    documents: Optional[List[LeaseDocument]] = []
    payments: Optional[List[LeasePayment]] = []
    isActive: bool
    status: str
    # Baseline reading IDs (esposte nella risposta)
    electricityReadingId: Optional[int] = None
    waterReadingId: Optional[int] = None
    gasReadingId: Optional[int] = None
    electricityLaundryReadingId: Optional[int] = None

    class Config:
        orm_mode = True

# ------------------ SCHEMA INVOICE ITEM ------------------
class InvoiceItemBase(CamelCaseModel):
    invoiceId: Optional[int] = None
    description: str
    amount: float
    type: str

class InvoiceItemCreate(InvoiceItemBase):
    pass

class InvoiceItem(InvoiceItemBase):
    id: int
    createdAt: datetime
    updatedAt: datetime

# ------------------ SCHEMA PAYMENT RECORD ------------------
class PaymentRecordBase(CamelCaseModel):
    invoiceId: int
    amount: float
    paymentDate: date
    paymentMethod: str
    reference: Optional[str] = None
    notes: Optional[str] = None

class PaymentRecordCreate(PaymentRecordBase):
    pass

class PaymentRecord(PaymentRecordBase):
    id: int
    createdAt: datetime
    updatedAt: datetime

# ------------------ SCHEMA INVOICE ------------------
class InvoiceBase(CamelCaseModel):
    leaseId: Optional[int] = None
    tenantId: Optional[int] = None
    apartmentId: Optional[int] = None
    invoiceNumber: str
    month: int
    year: int
    issueDate: date
    dueDate: date
    subtotal: Optional[float] = 0.0
    total: Optional[float] = 0.0
    isPaid: bool = False
    notes: Optional[str] = None
    reminderSent: bool = False
    reminderDate: Optional[date] = None

class InvoiceCreate(InvoiceBase):
    items: List[InvoiceItemCreate]

class Invoice(InvoiceBase):
    id: int
    createdAt: datetime
    updatedAt: datetime
    items: List[InvoiceItem] = []
    payments: List[PaymentRecord] = []

# ------------------ SCHEMA USER ------------------
class UserBase(CamelCaseModel):
    username: str
    email: EmailStr
    firstName: str = Field(alias='first_name')
    lastName: str = Field(alias='last_name')
    role: str
    isActive: bool = Field(alias='is_active', default=True)

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    lastLogin: Optional[datetime] = Field(alias='last_login', default=None)
    createdAt: datetime = Field(alias='created_at')
    updatedAt: datetime = Field(alias='updated_at')

    class Config:
        from_attributes = True
        populate_by_name = True

class UserLogin(CamelCaseModel):
    username: str
    password: str

class UserPasswordChange(CamelCaseModel):
    currentPassword: str
    newPassword: str

# ------------------ SCHEMA TOKEN ------------------
class Token(CamelCaseModel):
    accessToken: str
    tokenType: str

class TokenPair(CamelCaseModel):
    accessToken: str
    refreshToken: str
    tokenType: str
    expiresIn: int

class TokenData(CamelCaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

# ------------------ SCHEMA UTILITY SUMMARY E STATISTICHE ------------------
class UtilitySummary(CamelCaseModel):
    apartmentId: int
    apartmentName: str
    month: int
    year: int
    electricity: Dict[str, float]  # {"consumption": float, "cost": float, "readingsCount": int}
    water: Dict[str, float]  # {"consumption": float, "cost": float, "readingsCount": int}
    gas: Dict[str, float]  # {"consumption": float, "cost": float, "readingsCount": int}
    totalCost: float

class MonthlyUtilityData(CamelCaseModel):
    month: int
    year: int
    apartmentId: int
    apartmentName: str
    electricity: float  # Solo elettricità principale
    water: float
    gas: float
    electricityCost: float  # Solo costo elettricità principale
    waterCost: float
    gasCost: float
    laundryElectricity: float  # Elettricità lavanderia
    laundryElectricityCost: float  # Costo elettricità lavanderia
    totalCost: float

class MonthlyData(CamelCaseModel):
    month: int
    monthName: str
    electricity: float  # Solo elettricità principale
    water: float
    gas: float
    electricityCost: float  # Solo costo elettricità principale
    waterCost: float
    gasCost: float
    laundryElectricity: float  # Elettricità lavanderia
    laundryElectricityCost: float  # Costo elettricità lavanderia
    totalCost: float

class YearlyTotals(CamelCaseModel):
    electricity: float  # Solo elettricità principale
    water: float
    gas: float
    laundryElectricity: float  # Elettricità lavanderia
    totalCost: float

class ApartmentUtilityData(CamelCaseModel):
    apartmentId: int
    apartmentName: str
    monthlyData: List[MonthlyData]
    yearlyTotals: YearlyTotals

class UtilityStatistics(CamelCaseModel):
    totalApartments: int
    totalConsumption: Dict[str, float]  # {"electricity": float, "water": float, "gas": float}
    totalCosts: Dict[str, float]  # {"electricity": float, "water": float, "gas": float, "total": float}
    averageConsumption: Dict[str, float]  # {"electricity": float, "water": float, "gas": float}
    monthlyTrend: List[Dict[str, Union[int, str, float]]]  # [{"month": int, "monthName": str, "totalConsumption": float, "totalCost": float}]

class LastReading(CamelCaseModel):
    apartmentId: int
    type: str
    lastReading: float
    lastReadingDate: date
    hasHistory: bool
    subtype: Optional[str] = None

class UtilityFormData(CamelCaseModel):
    apartmentId: int
    type: str
    readingDate: date
    currentReading: float
    unitCost: float
    notes: Optional[str] = None
    subtype: Optional[str] = None
    isSpecialReading: Optional[bool] = None

class UtilityTypeConfig(CamelCaseModel):
    type: str
    label: str
    unit: str
    icon: str
    color: str
    defaultCost: float


# ------------------ SCHEMA BILLING DEFAULTS ------------------
class UnitCosts(CamelCaseModel):
    electricity: float = Field(ge=0)
    water: float = Field(ge=0)
    gas: float = Field(ge=0)


class BillingDefaultsRead(CamelCaseModel):
    tari: float
    meterFee: float
    unitCosts: UnitCosts

    class Config:
        from_attributes = True


class BillingDefaultsUpdate(CamelCaseModel):
    tari: float | None = Field(default=None, ge=0)
    meterFee: float | None = Field(default=None, ge=0)
    unitCosts: UnitCosts | None = None

# ------------------ SCHEMA INVOICE AUTOMATION ------------------
class InvoiceAutomationRead(CamelCaseModel):
    automationType: str
    automationDays: int

class InvoiceAutomationUpdate(CamelCaseModel):
    automationType: Optional[str] = None
    automationDays: Optional[int] = Field(None, ge=0)