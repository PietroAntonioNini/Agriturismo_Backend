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
    year: Optional[int] = None,
    month: Optional[int] = None,
    isPaid: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    return service.get_utility_readings(db, skip, limit, apartmentId, type, year, month, isPaid)

# GET utility reading by ID
@router.get("/{reading_id}", response_model=schemas.UtilityReading)
def get_utility_reading(reading_id: int, db: Session = Depends(get_db)):
    reading = service.get_utility_reading(db, reading_id)
    if reading is None:
        raise HTTPException(status_code=404, detail="Utility reading not found")
    return reading

# POST create utility reading
@router.post("/", response_model=schemas.UtilityReading, status_code=status.HTTP_201_CREATED)
def create_utility_reading(reading: schemas.UtilityReadingCreate, db: Session = Depends(get_db)):
    # Verifica che l'appartamento esista
    apartment = service.get_apartment(db, reading.apartmentId)
    if not apartment:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    # Prendi l'ultima lettura dello stesso tipo per calcolare il consumo
    last_reading = service.get_last_utility_reading(db, reading.apartmentId, reading.type)
    
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
    return service.create_utility_reading(db, reading)

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
    db: Session = Depends(get_db)
):
    apartment = service.get_apartment(db, apartmentId)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    return service.get_utility_readings(db, apartmentId=apartmentId, type=type, year=year, month=month)

# GET last utility reading for an apartment and type
@router.get("/apartment/{apartmentId}/last/{type}", response_model=schemas.UtilityReading)
def get_last_utility_reading_by_type(
    apartmentId: int,
    type: str,
    db: Session = Depends(get_db)
):
    apartment = service.get_apartment(db, apartmentId)
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