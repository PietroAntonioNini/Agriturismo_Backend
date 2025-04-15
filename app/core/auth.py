from datetime import datetime, timedelta
from jose import jwt, JWTError
from typing import Optional, Tuple
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import ValidationError
import logging
import uuid

from app.config import settings
from app.models.models import User as UserModel, RefreshToken
from app.schemas.schemas import TokenData
from app.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

logger = logging.getLogger(__name__)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a new JWT token with the given data and expiration time
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def create_refresh_token(username: str, db: Session) -> str:
    """
    Create a new refresh token and store it in the database
    """
    # Generate a random token
    token_value = str(uuid.uuid4())
    
    # Set expiration date (longer than access token)
    expires = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    
    # Create DB record
    db_token = RefreshToken(
        token=token_value,
        username=username,
        expires=expires
    )
    
    # Save to DB
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    
    logger.info(f"Creato nuovo refresh token per {username}, scade il {expires}")
    return token_value

def verify_refresh_token(token: str, db: Session) -> Tuple[bool, Optional[str]]:
    """
    Verify a refresh token and return the username if valid
    """
    # Find token in DB
    db_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    
    if not db_token:
        logger.warning(f"Refresh token non trovato nel database")
        return False, None
    
    # Check if expired
    if db_token.expires < datetime.utcnow():
        logger.warning(f"Refresh token scaduto per {db_token.username}")
        # Delete expired token
        db.delete(db_token)
        db.commit()
        return False, None
    
    # Check if revoked
    if db_token.is_revoked:
        logger.warning(f"Refresh token revocato per {db_token.username}")
        return False, None
    
    logger.info(f"Refresh token valido per {db_token.username}")
    return True, db_token.username

def revoke_refresh_token(token: str, db: Session) -> bool:
    """
    Revoke a refresh token
    """
    db_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    
    if not db_token:
        return False
    
    # Set revoked flag
    db_token.is_revoked = True
    db.commit()
    
    logger.info(f"Refresh token revocato per {db_token.username}")
    return True

def revoke_all_user_tokens(username: str, db: Session) -> int:
    """
    Revoke all refresh tokens for a user
    """
    # Get all active tokens for the user
    tokens = db.query(RefreshToken).filter(
        RefreshToken.username == username,
        RefreshToken.is_revoked == False,
        RefreshToken.expires > datetime.utcnow()
    ).all()
    
    # Revoke all
    for token in tokens:
        token.is_revoked = True
    
    db.commit()
    logger.info(f"Revocati {len(tokens)} refresh token per {username}")
    return len(tokens)

def verify_token(token: str, credentials_exception):
    """
    Verify a JWT token and return the decoded data
    """
    try:
        # Verifica che il token non sia undefined o invalido
        if token is None or token == "undefined" or token.lower() == "bearer":
            logger.error("Token è None, 'undefined' o solo 'Bearer'")
            raise credentials_exception
            
        logger.info(f"Verifica token: {token[:15]}...")
        
        # Rimuovi eventuali prefissi 'Bearer ' non necessari
        if token.lower().startswith("bearer "):
            token = token[7:]
            logger.info("Rimosso prefisso 'Bearer ' dal token")
        
        payload = jwt.decode(
            token, 
            settings.secret_key, 
            algorithms=[settings.algorithm]
        )
        logger.info(f"Token decodificato con successo: {payload}")
        username: str = payload.get("sub")
        role: str = payload.get("role", "")
        if username is None:
            logger.warning("Token mancante del campo 'sub'")
            raise credentials_exception
        token_data = TokenData(username=username, role=role)
        return token_data
    except JWTError as e:
        logger.error(f"Errore nella verifica del token: {str(e)}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Errore imprevisto nella verifica del token: {str(e)}")
        raise credentials_exception

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Get the current user from the JWT token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    logger.info("Tentativo di ottenere utente corrente da token")
    try:
        if token is None:
            logger.error("Token è None - Authorization header mancante")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = verify_token(token, credentials_exception)
        logger.info(f"Token verificato per username: {token_data.username}")
        
        user = db.query(UserModel).filter(UserModel.username == token_data.username).first()
        if user is None:
            logger.warning(f"Utente {token_data.username} non trovato nel database")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"User '{token_data.username}' not found in database",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        logger.info(f"Utente trovato: {user}")
        # Update last login time
        user.lastLogin = datetime.utcnow()
        db.commit()
        return user
    except HTTPException as h:
        # Rilanciamo le eccezioni HTTP così come sono
        raise h
    except Exception as e:
        logger.error(f"Errore durante get_current_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_active_user(current_user: UserModel = Depends(get_current_user)):
    """
    Check if the current user is active
    """
    if not current_user.isActive:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user 