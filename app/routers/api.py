from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import models
from app.schemas import schemas
from app.services import service

# Questa riga è cruciale e non deve mancare
router = APIRouter()

# Poi seguono tutte le definizioni di rotte
@router.post("/accommodations/", response_model=schemas.Accommodation, status_code=status.HTTP_201_CREATED, tags=["accommodations"])
def create_accommodation(accommodation: schemas.AccommodationCreate, db: Session = Depends(get_db)):
    return service.create_accommodation(db=db, accommodation=accommodation)

# ... altre rotte ...