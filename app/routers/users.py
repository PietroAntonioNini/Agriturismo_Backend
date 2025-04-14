from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.schemas import User
from app.models.models import User as UserModel
from app.core.auth import get_current_active_user

router = APIRouter(
    prefix="/api/users",
    tags=["Users"],
    responses={401: {"description": "Unauthorized"}},
)

@router.get("/me", response_model=User)
async def read_users_me(current_user: UserModel = Depends(get_current_active_user)):
    """
    Get current user information
    """
    return current_user

@router.get("/", response_model=List[User])
async def read_users(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 100
):
    """
    Retrieve users (admin only)
    """
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    users = db.query(UserModel).offset(skip).limit(limit).all()
    return users
