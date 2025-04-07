from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from datetime import datetime
import os
import shutil

from app.database import get_db
from app.models import models
from app.schemas import schemas
from app.services import service

router = APIRouter(
    prefix="/apartments",
    tags=["apartments"]
)

# GET all apartments with optional filters
@router.get("/", response_model=List[schemas.Apartment])
def get_apartments(
    skip: int = 0, 
    limit: int = 100, 
    isAvailable: Optional[bool] = None,
    status: Optional[str] = None,
    floor: Optional[int] = None,
    minRooms: Optional[int] = None,
    maxPrice: Optional[float] = None,
    hasBalcony: Optional[bool] = None,
    hasParking: Optional[bool] = None,
    isFurnished: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    return service.get_apartments(
        db, skip, limit, isAvailable, status, floor,
        minRooms, maxPrice, hasBalcony, hasParking, isFurnished
    )

# GET apartment by ID
@router.get("/{apartmentId}", response_model=schemas.Apartment)
def get_apartment(apartmentId: int, db: Session = Depends(get_db)):
    apartment = service.get_apartment(db, apartmentId)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return apartment

# POST create apartment
@router.post("/", response_model=schemas.Apartment, status_code=status.HTTP_201_CREATED)
def create_apartment(apartment: schemas.ApartmentCreate, db: Session = Depends(get_db)):
    return service.create_apartment(db, apartment)

# POST create apartment with images
@router.post("/with-images", response_model=schemas.Apartment, status_code=status.HTTP_201_CREATED)
async def create_apartment_with_images(
    apartment: str = Form(...),
    files: List[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    apartment_data = json.loads(apartment)
    apartment_obj = schemas.ApartmentCreate(**apartment_data)
    
    # Create the apartment first
    new_apartment = service.create_apartment(db, apartment_obj)
    
    # Handle file uploads if any
    if files:
        image_urls = await service.save_apartment_images(new_apartment.id, files)
        # Update the apartment with image URLs
        new_apartment = service.update_apartment_images(db, new_apartment.id, image_urls)
    
    return new_apartment

# PUT update apartment
@router.put("/{apartmentId}", response_model=schemas.Apartment)
def update_apartment(
    apartmentId: int,
    apartment: schemas.ApartmentCreate,
    db: Session = Depends(get_db)
):
    existing_apartment = service.get_apartment(db, apartmentId)
    if existing_apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return service.update_apartment(db, apartmentId, apartment)

# PUT update apartment with images
@router.put("/{apartmentId}/with-images", response_model=schemas.Apartment)
async def update_apartment_with_images(
    apartmentId: int,
    apartment: str = Form(...),
    files: List[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    existing_apartment = service.get_apartment(db, apartmentId)
    if existing_apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    apartment_data = json.loads(apartment)
    apartment_obj = schemas.ApartmentCreate(**apartment_data)
    
    # Update the apartment data
    updated_apartment = service.update_apartment(db, apartmentId, apartment_obj)
    
    # Handle file uploads if any
    if files:
        image_urls = await service.save_apartment_images(apartmentId, files)
        # Merge with existing images or replace them
        updated_apartment = service.update_apartment_images(db, apartmentId, image_urls, append=True)
    
    return updated_apartment

# DELETE apartment
@router.delete("/{apartmentId}", status_code=status.HTTP_204_NO_CONTENT)
def delete_apartment(apartmentId: int, db: Session = Depends(get_db)):
    existing_apartment = service.get_apartment(db, apartmentId)
    if existing_apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    # First, delete the apartment from the database
    service.delete_apartment(db, apartmentId)
    
    # Then, delete the associated image folder
    try:
        # Construct the path to the apartment's image folder
        folder_path = os.path.join("static", "apartments", str(apartmentId))
        
        # Check if the folder exists
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            # Delete the folder and all its contents
            shutil.rmtree(folder_path)
            print(f"Successfully deleted image folder for apartment {apartmentId}")
        else:
            print(f"No image folder found for apartment {apartmentId}")
            
    except Exception as e:
        # Log the error but don't fail the request
        print(f"Error deleting image folder for apartment {apartmentId}: {str(e)}")
        
    return {"detail": "Apartment deleted successfully"}

# PATCH update apartment status
@router.patch("/{apartmentId}/status", response_model=schemas.Apartment)
def update_apartment_status(
    apartmentId: int,
    status_data: dict,
    db: Session = Depends(get_db)
):
    existing_apartment = service.get_apartment(db, apartmentId)
    if existing_apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    if "status" not in status_data:
        raise HTTPException(status_code=400, detail="Status field is required")
    
    return service.update_apartment_status(db, apartmentId, status_data["status"])

# GET apartment's tenants
@router.get("/{apartmentId}/tenants", response_model=List[schemas.Tenant])
def get_apartment_tenants(apartmentId: int, db: Session = Depends(get_db)):
    apartment = service.get_apartment(db, apartmentId)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return service.get_apartment_tenants(db, apartmentId)

# GET apartment's utility readings
@router.get("/{apartmentId}/utilities", response_model=List[schemas.UtilityReading])
def get_apartment_utilities(
    apartmentId: int,
    type: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db)
):
    apartment = service.get_apartment(db, apartmentId)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return service.get_apartment_utilities(db, apartmentId, type, year, month)

# GET apartment's maintenance records
@router.get("/{apartmentId}/maintenance", response_model=List[schemas.MaintenanceRecord])
def get_apartment_maintenance(
    apartmentId: int,
    type: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    apartment = service.get_apartment(db, apartmentId)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return service.get_apartment_maintenance(db, apartmentId, type, from_date, to_date)

# GET apartment's leases
@router.get("/{apartmentId}/leases", response_model=List[schemas.Lease])
def get_apartment_leases(
    apartmentId: int,
    isActive: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    apartment = service.get_apartment(db, apartmentId)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return service.get_apartment_leases(db, apartmentId, isActive)

# GET apartment's invoices
@router.get("/{apartmentId}/invoices", response_model=List[schemas.Invoice])
def get_apartment_invoices(
    apartmentId: int,
    isPaid: Optional[bool] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db)
):
    apartment = service.get_apartment(db, apartmentId)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return service.get_apartment_invoices(db, apartmentId, isPaid, year, month)

# POST upload apartment image
@router.post("/{apartmentId}/images", response_model=dict)
async def upload_apartment_image(
    apartmentId: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    apartment = service.get_apartment(db, apartmentId)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    image_url = await service.save_apartment_image(apartmentId, image)
    service.add_apartment_image(db, apartmentId, image_url)
    
    return {"imageUrl": image_url}

# DELETE apartment image
@router.delete("/{apartmentId}/images/{image_name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_apartment_image(
    apartmentId: int,
    image_name: str,
    db: Session = Depends(get_db)
):
    apartment = service.get_apartment(db, apartmentId)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    success = service.delete_apartment_image(db, apartmentId, image_name)
    if not success:
        raise HTTPException(status_code=404, detail="Image not found")
    
    return {"detail": "Image deleted successfully"}

# GET available apartments
@router.get("/available/list", response_model=List[schemas.Apartment])
def get_available_apartments(db: Session = Depends(get_db)):
    return service.get_apartments(db, isAvailable=True)

# GET search apartments
@router.get("/search/", response_model=List[schemas.Apartment])
def search_apartments(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db)
):
    return service.search_apartments(db, q)