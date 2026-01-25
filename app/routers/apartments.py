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

from app.core.auth import get_current_active_user

router = APIRouter(
    prefix="/apartments",
    tags=["apartments"]
)

# GET all apartments with optional filters
@router.get("/", response_model=List[schemas.Apartment])
def get_apartments(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    floor: Optional[int] = None,
    minRooms: Optional[int] = None,
    maxPrice: Optional[float] = None,
    hasBalcony: Optional[bool] = None,
    hasParking: Optional[bool] = None,
    isFurnished: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    return service.get_apartments(
        db, skip, limit, status, floor,
        minRooms, maxPrice, hasBalcony, hasParking, isFurnished, current_user.id
    )

# GET apartment by ID
@router.get("/{apartmentId}", response_model=schemas.Apartment)
def get_apartment(apartmentId: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    apartment = service.get_apartment(db, apartmentId, current_user.id)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    # Sincronizza automaticamente le immagini con il filesystem
    sync_result = service.sync_apartment_images_with_filesystem(db, apartmentId)
    if sync_result and sync_result["removed_orphaned_images"]:
        print(f"Sincronizzate immagini per appartamento {apartmentId}: rimossi {len(sync_result['removed_orphaned_images'])} riferimenti orfani")
        # Ricarica l'appartamento dopo la sincronizzazione
        apartment = service.get_apartment(db, apartmentId)
    
    return apartment

# POST create apartment
@router.post("/", response_model=schemas.Apartment, status_code=status.HTTP_201_CREATED)
def create_apartment(
    apartment: schemas.ApartmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    return service.create_apartment(db, apartment, user_id=current_user.id)

# POST create apartment with images
@router.post("/with-images", response_model=schemas.Apartment, status_code=status.HTTP_201_CREATED)
async def create_apartment_with_images(
    apartment: str = Form(...),
    files: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    apartment_data = json.loads(apartment)
    apartment_obj = schemas.ApartmentCreate(**apartment_data)
    
    # Create the apartment first
    new_apartment = service.create_apartment(db, apartment_obj, user_id=current_user.id)
    
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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    existing_apartment = service.get_apartment(db, apartmentId, current_user.id)
    if existing_apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return service.update_apartment(db, apartmentId, apartment)

# PUT update apartment with images
@router.put("/{apartmentId}/with-images", response_model=schemas.Apartment)
async def update_apartment_with_images(
    apartmentId: int,
    apartment: str = Form(...),
    files: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    existing_apartment = service.get_apartment(db, apartmentId, current_user.id)
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
    
    # Sincronizza automaticamente le immagini con il filesystem dopo l'aggiornamento
    sync_result = service.sync_apartment_images_with_filesystem(db, apartmentId)
    if sync_result and sync_result["removed_orphaned_images"]:
        print(f"Sincronizzate immagini durante aggiornamento appartamento {apartmentId}: rimossi {len(sync_result['removed_orphaned_images'])} riferimenti orfani")
        # Ricarica l'appartamento dopo la sincronizzazione
        updated_apartment = service.get_apartment(db, apartmentId, current_user.id)
    
    return updated_apartment

# DELETE apartment
@router.delete("/{apartmentId}", status_code=status.HTTP_204_NO_CONTENT)
def delete_apartment(apartmentId: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    existing_apartment = service.get_apartment(db, apartmentId, current_user.id)
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
def get_apartment_tenants(apartmentId: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    apartment = service.get_apartment(db, apartmentId, user_id=current_user.id)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return service.get_apartment_tenants(db, apartmentId, user_id=current_user.id)

# GET apartment's utility readings
@router.get("/{apartmentId}/utilities", response_model=List[schemas.UtilityReading])
def get_apartment_utilities(
    apartmentId: int,
    type: Optional[str] = None,
    subtype: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    apartment = service.get_apartment(db, apartmentId, user_id=current_user.id)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return service.get_apartment_utilities(db, apartmentId, type, subtype, year, month, user_id=current_user.id)

# GET apartment's maintenance records
@router.get("/{apartmentId}/maintenance", response_model=List[schemas.MaintenanceRecord])
def get_apartment_maintenance(
    apartmentId: int,
    type: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    apartment = service.get_apartment(db, apartmentId, user_id=current_user.id)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return service.get_apartment_maintenance(db, apartmentId, type, from_date, to_date, user_id=current_user.id)

# GET apartment's leases
@router.get("/{apartmentId}/leases", response_model=List[schemas.Lease])
def get_apartment_leases(
    apartmentId: int,
    isActive: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    apartment = service.get_apartment(db, apartmentId, user_id=current_user.id)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return service.get_apartment_leases(db, apartmentId, isActive, user_id=current_user.id)

# GET apartment's invoices
@router.get("/{apartmentId}/invoices", response_model=List[schemas.Invoice])
def get_apartment_invoices(
    apartmentId: int,
    isPaid: Optional[bool] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    apartment = service.get_apartment(db, apartmentId, user_id=current_user.id)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return service.get_apartment_invoices(db, apartmentId, isPaid, year, month, user_id=current_user.id)

# POST upload apartment image
@router.post("/{apartmentId}/images", response_model=dict)
async def upload_apartment_image(
    apartmentId: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    apartment = service.get_apartment(db, apartmentId, user_id=current_user.id)
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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    apartment = service.get_apartment(db, apartmentId, user_id=current_user.id)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
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

# POST sync apartment images with filesystem
@router.post("/{apartmentId}/sync-images", response_model=dict)
def sync_apartment_images(apartmentId: int, db: Session = Depends(get_db)):
    """Sincronizza le immagini dell'appartamento nel database con quelle fisicamente presenti nel filesystem."""
    apartment = service.get_apartment(db, apartmentId)
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    sync_result = service.sync_apartment_images_with_filesystem(db, apartmentId)
    
    if sync_result is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    return {
        "message": "Sincronizzazione completata",
        "orphaned_images_removed": sync_result["removed_orphaned_images"],
        "current_images": sync_result["current_images"],
        "removed_count": len(sync_result["removed_orphaned_images"])
    }

# POST sync all apartments images with filesystem
@router.post("/sync-all-images", response_model=dict)
def sync_all_apartments_images(db: Session = Depends(get_db)):
    """Sincronizza le immagini di tutti gli appartamenti nel database con quelle fisicamente presenti nel filesystem."""
    apartments = service.get_apartments(db, skip=0, limit=1000)  # Prendi tutti gli appartamenti
    
    total_orphaned_removed = 0
    processed_apartments = 0
    sync_results = []
    
    for apartment in apartments:
        sync_result = service.sync_apartment_images_with_filesystem(db, apartment.id)
        if sync_result:
            orphaned_count = len(sync_result["removed_orphaned_images"])
            if orphaned_count > 0:
                sync_results.append({
                    "apartment_id": apartment.id,
                    "apartment_name": apartment.name,
                    "orphaned_images_removed": sync_result["removed_orphaned_images"],
                    "removed_count": orphaned_count
                })
                total_orphaned_removed += orphaned_count
            processed_apartments += 1
    
    return {
        "message": "Sincronizzazione completata per tutti gli appartamenti",
        "processed_apartments": processed_apartments,
        "total_orphaned_images_removed": total_orphaned_removed,
        "detailed_results": sync_results
    }

# GET available apartments
@router.get("/available/list", response_model=List[schemas.Apartment])
def get_available_apartments(db: Session = Depends(get_db)):
    return service.get_apartments(db, status="available")

# GET search apartments
@router.get("/search/", response_model=List[schemas.Apartment])
def search_apartments(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db)
):
    return service.search_apartments(db, q)