from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from typing import Any
import logging

from app.database import get_db
from app.schemas.schemas import UserCreate, User, Token, UserPasswordChange
from app.models.models import User as UserModel
from app.core.hashing import Hasher
from app.core.auth import (
    create_access_token, 
    get_current_user, 
    get_current_active_user,
    verify_token
)
from app.config import settings

# Configurazione del logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
    responses={401: {"description": "Unauthorized"}},
)

@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    # Authenticate user
    user = db.query(UserModel).filter(UserModel.username == form_data.username).first()
    if not user or not Hasher.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login time
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return {"accessToken": access_token, "tokenType": "bearer"}

@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    Register a new user
    """
    try:
        # Log dei dati ricevuti
        logger.info(f"Registrazione utente: {user_in.dict()}")
        
        # Check if username already exists
        db_user_by_username = db.query(UserModel).filter(UserModel.username == user_in.username).first()
        if db_user_by_username:
            logger.warning(f"Username {user_in.username} già registrato")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered",
            )
        
        # Check if email already exists
        db_user_by_email = db.query(UserModel).filter(UserModel.email == user_in.email).first()
        if db_user_by_email:
            logger.warning(f"Email {user_in.email} già registrata")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        
        # Create new user
        logger.info("Generazione password hash...")
        hashed_password = Hasher.get_password_hash(user_in.password)
        
        # Log dei campi che saranno inseriti nel modello
        logger.info(f"Creazione utente con: username={user_in.username}, email={user_in.email}, first_name={user_in.firstName}, last_name={user_in.lastName}, role={user_in.role}")
        
        # Crea l'utente con i campi mappati correttamente
        db_user = UserModel(
            username=user_in.username,
            email=user_in.email,
            hashed_password=hashed_password,
            first_name=user_in.firstName,
            last_name=user_in.lastName,
            role=user_in.role,
            is_active=user_in.isActive
        )
        
        logger.info("Aggiunta dell'utente al database...")
        db.add(db_user)
        logger.info("Commit della transazione...")
        db.commit()
        logger.info("Refresh dell'oggetto db_user...")
        db.refresh(db_user)
        
        logger.info(f"Utente registrato con successo: {db_user.username}, id: {db_user.id}")
        return db_user
    except Exception as e:
        logger.error(f"Errore durante la registrazione: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Fai il rollback in caso di errore
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore interno del server: {str(e)}"
        )

@router.post("/refresh-token", response_model=Token)
async def refresh_token(
    current_user: UserModel = Depends(get_current_active_user),
) -> Any:
    """
    Refresh token
    """
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": current_user.username, "role": current_user.role},
        expires_delta=access_token_expires
    )
    
    return {"accessToken": access_token, "tokenType": "bearer"}

@router.put("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: UserPasswordChange,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Change user password
    """
    try:
        # Verify current password
        if not Hasher.verify_password(password_data.currentPassword, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password",
            )
        
        # Update password
        current_user.hashed_password = Hasher.get_password_hash(password_data.newPassword)
        db.commit()
        
        return {"message": "Password updated successfully"}
    except Exception as e:
        logger.error(f"Errore durante il cambio password: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore interno del server: {str(e)}"
        )
