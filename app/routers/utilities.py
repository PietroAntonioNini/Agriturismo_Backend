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
    apartment_id: Optional[int] = None,
    type: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    is_paid: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    return service.get_utility_readings(db, skip, limit, apartment_id, type, year, month, is_paid)

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
    apartment = service.get_apartment(db, reading.apartment_id)
    if not apartment:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    # Prendi l'ultima lettura dello stesso tipo per calcolare il consumo
    last_reading = service.get_last_utility_reading(db, reading.apartment_id, reading.type)
    
    # Se c'è una lettura precedente, calcola il consumo
    if last_reading:
        # Verifica che la nuova lettura sia maggiore dell'ultima
        if reading.current_reading < last_reading.current_reading:
            raise HTTPException(
                status_code=400, 
                detail=f"Current reading must be greater than the last reading ({last_reading.current_reading})"
            )
        
        # Aggiorna la lettura precedente
        reading.previous_reading = last_reading.current_reading
    
    # Calcola il consumo
    reading.consumption = reading.current_reading - reading.previous_reading
    
    # Calcola il costo totale
    reading.total_cost = reading.consumption * reading.unit_cost
    
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
    reading.consumption = reading.current_reading - reading.previous_reading
    
    # Calcola il costo totale
    reading.total_cost = reading.consumption * reading.unit_cost
    
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
    
    if existing_reading.is_paid:
        raise HTTPException(status_code=400, detail="Utility reading is already marked as paid")
    
    # Aggiorna la lettura
    existing_reading.is_paid = True
    existing_reading.paid_date = datetime.utcnow().date()
    existing_reading.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(existing_reading)
    
    return existing_reading

# GET utility readings by apartment
@router.get("/apartment/{apartment_id}", response_model=List[schemas.UtilityReading])
def get_apartment_utility_readings(
    apartment_id: int,
    type: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db)
):
    apartment = service.get_apartment(db, apartment_id)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    return service.get_utility_readings(db, apartment_id=apartment_id, type=type, year=year, month=month)

# GET last utility reading for an apartment and type
@router.get("/apartment/{apartment_id}/last/{type}", response_model=schemas.UtilityReading)
def get_last_utility_reading_by_type(
    apartment_id: int,
    type: str,
    db: Session = Depends(get_db)
):
    apartment = service.get_apartment(db, apartment_id)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    reading = service.get_last_utility_reading(db, apartment_id, type)
    if reading is None:
        raise HTTPException(status_code=404, detail=f"No {type} reading found for this apartment")
    
    return reading

# GET utility summary for an apartment
@router.get("/summary/{apartment_id}", response_model=List[schemas.UtilitySummary])
def get_utility_summary(
    apartment_id: int,
    year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    apartment = service.get_apartment(db, apartment_id)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    return service.get_utility_summary(db, apartment_id, year)

# GET yearly utility statistics
@router.get("/statistics/{year}", response_model=List[schemas.MonthlyUtilityData])
def get_yearly_utility_statistics(
    year: int,
    db: Session = Depends(get_db)
):
    return service.get_yearly_utility_statistics(db, year)

# GET apartment consumption by year
@router.get("/apartment/{apartment_id}/consumption/{year}", response_model=schemas.ApartmentUtilityData)
def get_apartment_consumption(
    apartment_id: int,
    year: int,
    db: Session = Depends(get_db)
):
    apartment = service.get_apartment(db, apartment_id)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    return service.get_apartment_consumption(db, apartment_id, year)

# GET unpaid utility readings
@router.get("/unpaid/list", response_model=List[schemas.UtilityReading])
def get_unpaid_utility_readings(db: Session = Depends(get_db)):
    return service.get_utility_readings(db, is_paid=False)