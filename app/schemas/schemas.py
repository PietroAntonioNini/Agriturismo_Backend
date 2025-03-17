from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date
from pydantic import BaseModel, EmailStr, validator, Field


# ------------------ SCHEMA UTILITY READING ------------------
class UtilityReadingBase(BaseModel):
    apartment_id: int
    type: str  # 'electricity', 'water', 'gas'
    reading_date: date
    previous_reading: float
    current_reading: float
    consumption: float
    unit_cost: float
    total_cost: float
    is_paid: bool = False
    notes: Optional[str] = None
    electricity_consumption: Optional[float] = None
    water_consumption: Optional[float] = None
    gas_consumption: Optional[float] = None
    electricity_cost: Optional[float] = None
    water_cost: Optional[float] = None
    gas_cost: Optional[float] = None

class UtilityReadingCreate(UtilityReadingBase):
    pass

class UtilityReading(UtilityReadingBase):
    id: int
    paid_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# ------------------ SCHEMA MAINTENANCE RECORD ------------------
class MaintenanceRecordBase(BaseModel):
    apartment_id: int
    type: str  # 'repair', 'inspection', 'upgrade', 'cleaning'
    description: str
    cost: float
    date: date
    completed_by: str
    notes: Optional[str] = None

class MaintenanceRecordCreate(MaintenanceRecordBase):
    pass

class MaintenanceRecord(MaintenanceRecordBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# ------------------ SCHEMA APARTMENT ------------------
class ApartmentBase(BaseModel):
    name: str
    description: Optional[str] = None
    floor: int
    square_meters: float
    rooms: int
    bathrooms: int
    has_balcony: bool = False
    has_parking: bool = False
    is_furnished: bool = False
    monthly_rent: float
    status: str  # 'available', 'occupied', 'maintenance'
    is_available: Optional[bool] = True
    notes: Optional[str] = None
    utility_meters_info: Optional[Dict[str, str]] = None
    amenities: Optional[List[str]] = None
    images: Optional[List[str]] = None

class ApartmentCreate(ApartmentBase):
    pass

class Apartment(ApartmentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    utility_readings: Optional[List[UtilityReading]] = []
    maintenance_records: Optional[List[MaintenanceRecord]] = []

    class Config:
        orm_mode = True


# ------------------ SCHEMA TENANT ------------------
# Base model that converts camelCase to snake_case and vice versa
class CamelCaseModel(BaseModel):
    class Config:
        # This works in both Pydantic v1 and v2
        populate_by_name = True  # Allow populating by alias
        alias_generator = lambda s: ''.join(word.capitalize() if i else word 
                                           for i, word in enumerate(s.split('_')))

# Now use this as the base for all your models
class CommunicationPreferences(CamelCaseModel):
    email: bool = True
    sms: bool = True
    whatsapp: bool = False

# Update your TenantBase model
class TenantBase(CamelCaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: str
    document_type: str
    document_number: str
    document_expiry_date: date
    document_front_image: Optional[str] = None
    document_back_image: Optional[str] = None
    address: Optional[str] = None
    communication_preferences: CommunicationPreferences
    notes: Optional[str] = None
    
    # Add a validator to handle ISO date strings
    @validator('document_expiry_date', pre=True)
    def parse_date(cls, value):
        if isinstance(value, str):
            # Handle ISO format with time
            if 'T' in value:
                value = value.split('T')[0]
            return datetime.strptime(value, '%Y-%m-%d').date()
        return value

class TenantCreate(TenantBase):
    pass

class Tenant(TenantBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True  # For Pydantic v1
        from_attributes = True  # For Pydantic v2


# ------------------ SCHEMA LEASE DOCUMENT ------------------
class LeaseDocumentBase(BaseModel):
    lease_id: int
    name: str
    type: str
    url: str
    upload_date: date

class LeaseDocumentCreate(LeaseDocumentBase):
    pass

class LeaseDocument(LeaseDocumentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# ------------------ SCHEMA LEASE PAYMENT ------------------
class LeasePaymentBase(BaseModel):
    lease_id: int
    amount: float
    payment_date: date
    payment_type: str
    reference: str
    notes: Optional[str] = None

class LeasePaymentCreate(LeasePaymentBase):
    pass

class LeasePayment(LeasePaymentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# ------------------ SCHEMA LEASE ------------------
class LeaseBase(BaseModel):
    tenant_id: int
    apartment_id: int
    start_date: date
    end_date: date
    monthly_rent: float
    security_deposit: float
    is_active: bool = True
    payment_due_day: int
    terms_and_conditions: str
    special_clauses: Optional[str] = None
    notes: Optional[str] = None

class LeaseCreate(LeaseBase):
    pass

class Lease(LeaseBase):
    id: int
    created_at: datetime
    updated_at: datetime
    documents: Optional[List[LeaseDocument]] = []
    payments: Optional[List[LeasePayment]] = []

    class Config:
        orm_mode = True


# ------------------ SCHEMA INVOICE ITEM ------------------
class InvoiceItemBase(BaseModel):
    invoice_id: int
    description: str
    amount: float
    type: str  # 'rent', 'electricity', 'water', 'gas', 'maintenance', 'other'

class InvoiceItemCreate(InvoiceItemBase):
    pass

class InvoiceItem(InvoiceItemBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# ------------------ SCHEMA PAYMENT RECORD ------------------
class PaymentRecordBase(BaseModel):
    invoice_id: int
    amount: float
    payment_date: date
    payment_method: str  # 'cash', 'bank_transfer', 'credit_card', 'check'
    reference: Optional[str] = None
    notes: Optional[str] = None

class PaymentRecordCreate(PaymentRecordBase):
    pass

class PaymentRecord(PaymentRecordBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# ------------------ SCHEMA INVOICE ------------------
class InvoiceBase(BaseModel):
    lease_id: int
    tenant_id: int
    apartment_id: int
    invoice_number: str
    month: int
    year: int
    issue_date: date
    due_date: date
    subtotal: float
    tax: float
    total: float
    is_paid: bool = False
    payment_date: Optional[date] = None
    payment_method: Optional[str] = None  # 'cash', 'bank_transfer', 'credit_card', 'check'
    notes: Optional[str] = None
    reminder_sent: bool = False
    reminder_date: Optional[date] = None

class InvoiceCreate(InvoiceBase):
    items: List[InvoiceItemCreate]

class Invoice(InvoiceBase):
    id: int
    created_at: datetime
    updated_at: datetime
    items: List[InvoiceItem] = []
    payments: List[PaymentRecord] = []

    class Config:
        orm_mode = True


# ------------------ SCHEMA USER ------------------
class UserBase(BaseModel):
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    role: str  # 'admin', 'manager', 'staff'
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# ------------------ SCHEMA UTILITY SUMMARY ------------------
class UtilitySummary(BaseModel):
    apartment_id: int
    month: int
    year: int
    electricity: dict
    water: dict
    gas: dict
    total_cost: float

class MonthlyUtilityData(BaseModel):
    month: int
    year: int
    apartment_id: int
    apartment_name: str
    electricity: float
    water: float
    gas: float

class ApartmentUtilityData(BaseModel):
    apartment_id: int
    apartment_name: str
    monthly_data: List[dict]

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None