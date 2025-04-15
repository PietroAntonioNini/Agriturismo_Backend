from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from typing import Any
import logging

from app.database import get_db
from app.schemas.schemas import UserCreate, User, Token, TokenPair, UserPasswordChange
from app.models.models import User as UserModel
from app.core.hashing import Hasher
from app.core.auth import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens,
    get_current_user, 
    get_current_active_user,
    verify_token
)
from app.config import settings
from app.utils.rate_limiter import limiter
from app.utils.csrf import generate_csrf_token, csrf_protect

# Configurazione del logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
    responses={401: {"description": "Unauthorized"}},
)

@router.post("/login", response_model=TokenPair)
@limiter.limit(settings.rate_limit_login)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """
    OAuth2 compatible token login, get access and refresh tokens for future requests
    """
    try:
        logger.info(f"Tentativo di login per l'utente: {form_data.username}")
        
        # Authenticate user
        user = db.query(UserModel).filter(UserModel.username == form_data.username).first()
        
        if not user:
            logger.warning(f"Login fallito: Utente '{form_data.username}' non trovato")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.info(f"Utente trovato: {user.username}, verifico password")
        logger.info(f"Password hash nel DB: {user.hashedPassword[:10]}...")
        
        password_correct = Hasher.verify_password(form_data.password, user.hashedPassword)
        logger.info(f"Verifica password: {'corretta' if password_correct else 'errata'}")
        
        if not password_correct:
            logger.warning(f"Login fallito: Password non corretta per l'utente '{form_data.username}'")
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
        
        # Create refresh token
        refresh_token = create_refresh_token(user.username, db)
        
        logger.info(f"Login riuscito per l'utente: {user.username} con ruolo: {user.role}")
        return {
            "accessToken": access_token, 
            "refreshToken": refresh_token,
            "tokenType": "bearer",
            "expiresIn": settings.access_token_expire_minutes * 60
        }
    except Exception as e:
        logger.error(f"Errore durante il login: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore interno del server durante il login: {str(e)}"
        )

@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_register)
async def register_user(
    request: Request,
    user_in: UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    Register a new user
    """
    try:
        # Log dei dati ricevuti
        logger.info(f"Registrazione utente: {user_in.dict()}")
        
        # Check database connection
        try:
            db_test = db.query(UserModel).first()
            logger.info(f"Database connection test: {'OK' if db is not None else 'FAILED'}")
        except Exception as db_error:
            logger.error(f"Database connection error: {str(db_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database connection error: {str(db_error)}"
            )
            
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
        
        # Password validation
        validate_password(user_in.password)
        
        # Create new user
        logger.info("Generazione password hash...")
        hashed_password = Hasher.get_password_hash(user_in.password)
        
        # Log dei campi che saranno inseriti nel modello
        logger.info(f"Creazione utente con: username={user_in.username}, email={user_in.email}, first_name={user_in.firstName}, last_name={user_in.lastName}, role={user_in.role}")
        
        # Inserisci l'utente nel database in una transazione
        try:
            # Crea l'utente con i campi mappati correttamente
            db_user = UserModel(
                username=user_in.username,
                email=user_in.email,
                hashedPassword=hashed_password,
                firstName=user_in.firstName,
                lastName=user_in.lastName,
                role=user_in.role,
                isActive=user_in.isActive
            )
            
            logger.info("Aggiunta dell'utente al database...")
            db.add(db_user)
            logger.info("Commit della transazione...")
            db.commit()
            logger.info("Refresh dell'oggetto db_user...")
            db.refresh(db_user)
            
            logger.info(f"Utente registrato con successo: {db_user.username}, id: {db_user.id}")
            
            # Restituisci direttamente l'oggetto SQLAlchemy. FastAPI/Pydantic gestiranno la serializzazione.
            return db_user
        except Exception as db_error:
            logger.error(f"Errore durante il salvataggio dell'utente: {str(db_error)}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Errore durante il salvataggio: {str(db_error)}"
            )
    except HTTPException as http_exc:
        # Non fare rollback per errori di validazione
        logger.warning(f"Validazione fallita durante la registrazione: {str(http_exc.detail)}")
        raise http_exc
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

@router.post("/refresh-token", response_model=TokenPair)
async def refresh_access_token(
    refresh_token: str = Body(..., embed=True),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get a new access token using a refresh token
    """
    try:
        logger.info("Richiesta refresh token")
        # Verify refresh token
        is_valid, username = verify_refresh_token(refresh_token, db)
        
        if not is_valid or not username:
            logger.warning(f"Refresh token non valido")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user
        user = db.query(UserModel).filter(UserModel.username == username).first()
        if not user or not user.isActive:
            logger.warning(f"Utente non trovato o non attivo: {username}")
            # Revoke the token since user is not active or does not exist
            revoke_refresh_token(refresh_token, db)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create new access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.username, "role": user.role},
            expires_delta=access_token_expires
        )
        
        # Create new refresh token and revoke the old one
        new_refresh_token = create_refresh_token(user.username, db)
        revoke_refresh_token(refresh_token, db)
        
        logger.info(f"Nuovo token generato per {user.username}")
        return {
            "accessToken": access_token, 
            "refreshToken": new_refresh_token,
            "tokenType": "bearer",
            "expiresIn": settings.access_token_expire_minutes * 60
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Errore durante il refresh del token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    refresh_token: str = Body(..., embed=True),
    db: Session = Depends(get_db)
) -> Any:
    """
    Logout a user by revoking their refresh token
    """
    try:
        revoke_refresh_token(refresh_token, db)
        return {"detail": "Successfully logged out"}
    except Exception as e:
        logger.error(f"Errore durante il logout: {str(e)}")
        # Continuiamo comunque
        return {"detail": "Successfully logged out"}

@router.post("/logout-all", status_code=status.HTTP_200_OK)
async def logout_all_devices(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Logout from all devices by revoking all refresh tokens
    """
    try:
        count = revoke_all_user_tokens(current_user.username, db)
        return {"detail": f"Successfully logged out from all devices ({count} sessions)"}
    except Exception as e:
        logger.error(f"Errore durante il logout da tutti i dispositivi: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/verify-token", status_code=status.HTTP_200_OK)
async def verify_token_validity(
    current_user: UserModel = Depends(get_current_active_user),
) -> Any:
    """
    Verifica se il token JWT è valido e restituisce informazioni sull'utente
    Questo endpoint può essere usato dal frontend per controllare se l'utente è autenticato
    """
    try:
        logger.info(f"Verificando validità token per utente: {current_user.username}")
        return {
            "valid": True,
            "username": current_user.username,
            "email": current_user.email,
            "role": current_user.role,
            "firstName": current_user.firstName,
            "lastName": current_user.lastName,
            "isActive": current_user.isActive
        }
    except Exception as e:
        logger.error(f"Errore durante la verifica del token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token non valido",
            headers={"WWW-Authenticate": "Bearer"},
        )

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
        
        # Validate new password
        validate_password(password_data.newPassword)
        
        # Update password
        current_user.hashed_password = Hasher.get_password_hash(password_data.newPassword)
        db.commit()
        
        # Logout from all other devices for security
        revoke_all_user_tokens(current_user.username, db)
        
        return {"message": "Password updated successfully"}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Errore durante il cambio password: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore interno del server: {str(e)}"
        )

@router.get("/csrf-token", status_code=status.HTTP_200_OK)
async def get_csrf_token(response: Response):
    """
    Genera un nuovo token CSRF e lo restituisce
    Il token viene impostato anche come cookie HttpOnly
    Il client deve includere il valore del token CSRF nell'header X-CSRF-Token per le richieste POST/PUT/DELETE
    """
    # Genera un nuovo token CSRF
    csrf_data = generate_csrf_token()
    
    # Imposta il cookie con il token
    cookie_options = {
        "key": "csrf_token",
        "value": csrf_data["token"],
        "httponly": True,
        "samesite": "lax",
        "secure": settings.enable_ssl_redirect,  # true in produzione con HTTPS
        "max_age": settings.csrf_token_expire_minutes * 60,
        "path": "/"
    }
    
    response.set_cookie(**cookie_options)
    
    # Restituisci il token CSRF al client
    return {
        "csrf_token": csrf_data["csrf_token"],
        "expires": csrf_data["expires"]
    }

# Funzione di supporto per la validazione della password
def validate_password(password: str) -> None:
    """
    Validate password strength based on settings
    """
    errors = []
    
    # Check minimum length
    if len(password) < settings.password_min_length:
        errors.append(f"Password deve essere di almeno {settings.password_min_length} caratteri")
    
    # Check for uppercase
    if settings.password_require_uppercase and not any(c.isupper() for c in password):
        errors.append("Password deve contenere almeno una lettera maiuscola")
    
    # Check for lowercase
    if settings.password_require_lowercase and not any(c.islower() for c in password):
        errors.append("Password deve contenere almeno una lettera minuscola")
    
    # Check for digit
    if settings.password_require_digit and not any(c.isdigit() for c in password):
        errors.append("Password deve contenere almeno un numero")
    
    # Check for special character
    if settings.password_require_special and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?/" for c in password):
        errors.append("Password deve contenere almeno un carattere speciale")
    
    # If any errors, raise exception
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Password non valida", "errors": errors}
        )
