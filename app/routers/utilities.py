from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import models
from app.schemas import schemas
from app.services import service

router = APIRouter(
    prefix="/utilities",
    tags=["utilities"]
)

# GET all utility readings with optional filters
@router.get("/", response_model=List[schemas.UtilityReading])
def get_utility_readings(
    skip: int = 0, 
    limit: int = 100,
    apartmentId: Optional[int] = None,
    type: Optional[str] = None,
    subtype: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    isPaid: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    return service.get_utility_readings(db, skip, limit, apartmentId, type, subtype, year, month, isPaid)

# GET utility type configurations
@router.get("/types", response_model=List[schemas.UtilityTypeConfig])
def get_utility_types():
    """Get available utility types with their configurations"""
    return [
        {
            "type": "electricity",
            "label": "Elettricità",
            "unit": "kWh",
            "icon": "bolt",
            "color": "#FFC107",
            "defaultCost": 0.22
        },
        {
            "type": "water",
            "label": "Acqua",
            "unit": "m³",
            "icon": "water_drop",
            "color": "#2196F3",
            "defaultCost": 2.50
        },
        {
            "type": "gas",
            "label": "Gas",
            "unit": "m³",
            "icon": "local_fire_department",
            "color": "#FF5722",
            "defaultCost": 1.20
        }
    ]

# GET utility reading by ID
@router.get("/{reading_id}", response_model=schemas.UtilityReading)
def get_utility_reading(reading_id: int, db: Session = Depends(get_db)):
    reading = service.get_utility_reading(db, reading_id)
    if reading is None:
        raise HTTPException(status_code=404, detail="Utility reading not found")
    return reading

# POST create utility reading
@router.post("/", response_model=schemas.UtilityReading, status_code=status.HTTP_201_CREATED)
def create_utility_reading(
    reading: schemas.UtilityReadingCreate,
    db: Session = Depends(get_db),
    user_id: int | None = Query(default=None, alias="user_id")
):
    # Verifica che l'appartamento esista
    apartment = service.get_apartment(db, reading.apartmentId)
    if not apartment:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    # Prendi l'ultima lettura dello stesso tipo e sottotipo per calcolare il consumo
    last_reading = service.get_last_utility_reading(db, reading.apartmentId, reading.type, reading.subtype)
    
    # Se c'è una lettura precedente, calcola il consumo
    if last_reading:
        # Verifica che la nuova lettura sia maggiore dell'ultima
        if reading.currentReading < last_reading.currentReading:
            raise HTTPException(
                status_code=400, 
                detail=f"Current reading must be greater than the last reading ({last_reading.currentReading})"
            )
        
        # Aggiorna la lettura precedente
        reading.previousReading = last_reading.currentReading
    
    # Calcola il consumo
    reading.consumption = reading.currentReading - reading.previousReading
    
    # Calcola il costo totale
    reading.totalCost = reading.consumption * reading.unitCost
    
    # Crea la lettura
    return service.create_utility_reading(db, reading, user_id=user_id)

# PUT update utility reading
@router.put("/{reading_id}", response_model=schemas.UtilityReading)
def update_utility_reading(
    reading_id: int,
    reading: schemas.UtilityReadingCreate,
    db: Session = Depends(get_db)
):
    existing_reading = service.get_utility_reading(db, reading_id)
    if existing_reading is None:
        raise HTTPException(status_code=404, detail="Utility reading not found")
    
    # Calcola il consumo
    reading.consumption = reading.currentReading - reading.previousReading
    
    # Calcola il costo totale
    reading.totalCost = reading.consumption * reading.unitCost
    
    return service.update_utility_reading(db, reading_id, reading)

# DELETE utility reading
@router.delete("/{reading_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_utility_reading(reading_id: int, db: Session = Depends(get_db)):
    existing_reading = service.get_utility_reading(db, reading_id)
    if existing_reading is None:
        raise HTTPException(status_code=404, detail="Utility reading not found")
    
    service.delete_utility_reading(db, reading_id)
    return {"detail": "Utility reading deleted successfully"}

# PATCH mark utility reading as paid
@router.patch("/{reading_id}/mark-paid", response_model=schemas.UtilityReading)
def mark_utility_reading_paid(
    reading_id: int,
    payment_data: dict,
    db: Session = Depends(get_db)
):
    existing_reading = service.get_utility_reading(db, reading_id)
    if existing_reading is None:
        raise HTTPException(status_code=404, detail="Utility reading not found")
    
    if existing_reading.isPaid:
        raise HTTPException(status_code=400, detail="Utility reading is already marked as paid")
    
    # Aggiorna la lettura
    existing_reading.isPaid = True
    existing_reading.paidDate = datetime.utcnow().date()
    existing_reading.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(existing_reading)
    
    return existing_reading

# GET utility readings by apartment
@router.get("/apartment/{apartmentId}", response_model=List[schemas.UtilityReading])
def get_apartment_utility_readings(
    apartmentId: int,
    type: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db),
    user_id: int | None = Query(default=None, alias="user_id")
):
    apartment = service.get_apartment(db, apartmentId, user_id)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    return service.get_utility_readings(db, apartmentId=apartmentId, type=type, year=year, month=month, user_id=user_id)

# GET last utility reading for an apartment and type
@router.get("/apartment/{apartmentId}/last/{type}", response_model=schemas.UtilityReading)
def get_last_utility_reading_by_type(
    apartmentId: int,
    type: str,
    db: Session = Depends(get_db),
    user_id: int | None = Query(default=None, alias="user_id")
):
    apartment = service.get_apartment(db, apartmentId, user_id)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    reading = service.get_last_utility_reading(db, apartmentId, type)
    if reading is None:
        raise HTTPException(status_code=404, detail=f"No {type} reading found for this apartment")
    
    return reading

# GET utility summary for an apartment
@router.get("/summary/{apartmentId}", response_model=List[schemas.UtilitySummary])
def get_utility_summary(
    apartmentId: int,
    year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    apartment = service.get_apartment(db, apartmentId)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    return service.get_utility_summary(db, apartmentId, year)

# GET yearly utility statistics
@router.get("/statistics/{year}", response_model=List[schemas.MonthlyUtilityData])
def get_yearly_utility_statistics(
    year: int,
    db: Session = Depends(get_db)
):
    return service.get_yearly_utility_statistics(db, year)

# GET apartment consumption by year
@router.get("/apartment/{apartmentId}/consumption/{year}", response_model=schemas.ApartmentUtilityData)
def get_apartment_consumption(
    apartmentId: int,
    year: int,
    db: Session = Depends(get_db)
):
    apartment = service.get_apartment(db, apartmentId)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    return service.get_apartment_consumption(db, apartmentId, year)

# GET unpaid utility readings
@router.get("/unpaid/list", response_model=List[schemas.UtilityReading])
def get_unpaid_utility_readings(db: Session = Depends(get_db)):
    return service.get_utility_readings(db, isPaid=False)

# GET utility statistics
@router.get("/statistics/overview", response_model=schemas.UtilityStatistics)
def get_utility_statistics_overview(
    year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    return service.get_utility_statistics_overview(db, year)

# GET last reading for apartment and type (for form auto-completion)
@router.get("/last-reading/{apartmentId}/{type}", response_model=schemas.LastReading)
def get_last_reading_info(
    apartmentId: int,
    type: str,
    subtype: Optional[str] = None,
    db: Session = Depends(get_db)
):
    apartment = service.get_apartment(db, apartmentId)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    last_reading = service.get_last_utility_reading(db, apartmentId, type, subtype)
    
    if last_reading is None:
        return {
            "apartmentId": apartmentId,
            "type": type,
            "lastReading": 0.0,
            "lastReadingDate": datetime.now().date(),
            "hasHistory": False,
            "subtype": subtype
        }
    
    return {
        "apartmentId": apartmentId,
        "type": type,
        "lastReading": last_reading.currentReading,
        "lastReadingDate": last_reading.readingDate,
        "hasHistory": True,
        "subtype": last_reading.subtype
    }

# BULK operations for multiple readings
@router.post("/bulk", response_model=List[schemas.UtilityReading])
def create_bulk_utility_readings(
    readings: List[schemas.UtilityReadingCreate],
    db: Session = Depends(get_db)
):
    """Create multiple utility readings at once"""
    created_readings = []
    
    for reading_data in readings:
        # Verify apartment exists
        apartment = service.get_apartment(db, reading_data.apartmentId)
        if not apartment:
            raise HTTPException(status_code=404, detail=f"Apartment {reading_data.apartmentId} not found")
        
        # Get last reading for calculation
        last_reading = service.get_last_utility_reading(db, reading_data.apartmentId, reading_data.type, reading_data.subtype)
        
        if last_reading:
            if reading_data.currentReading < last_reading.currentReading:
                raise HTTPException(
                    status_code=400,
                    detail=f"Current reading for apartment {reading_data.apartmentId} must be greater than the last reading ({last_reading.currentReading})"
                )
            reading_data.previousReading = last_reading.currentReading
        
        # Calculate consumption and cost
        reading_data.consumption = reading_data.currentReading - reading_data.previousReading
        reading_data.totalCost = reading_data.consumption * reading_data.unitCost
        
        # Create the reading
        created_reading = service.create_utility_reading(db, reading_data)
        created_readings.append(created_reading)
    
    return created_readings