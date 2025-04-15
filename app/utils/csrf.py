from fastapi import Request, HTTPException, status, Depends
from fastapi.security import APIKeyCookie
from jose import jwt, JWTError
from datetime import datetime, timedelta
import secrets
import logging

from app.config import settings

logger = logging.getLogger(__name__)

class CSRFError(Exception):
    pass

# Definizione del cookie CSRF
csrf_cookie = APIKeyCookie(name="csrf_token", auto_error=False)

def generate_csrf_token() -> dict:
    """
    Genera un nuovo token CSRF con una data di scadenza
    """
    expires = datetime.utcnow() + timedelta(minutes=settings.csrf_token_expire_minutes)
    
    # Genera un token random per prevenire CSRF
    csrf_token = secrets.token_hex(32)
    
    # Crea il JWT con il token CSRF
    token_data = {
        "csrf": csrf_token,
        "exp": expires
    }
    
    # Codifica il token
    encoded_token = jwt.encode(
        token_data, 
        settings.csrf_secret, 
        algorithm=settings.algorithm
    )
    
    return {
        "token": encoded_token,
        "csrf_token": csrf_token,
        "expires": expires
    }

def verify_csrf_token(token: str, header_token: str) -> bool:
    """
    Verifica che il token CSRF sia valido e corrisponda a quello nell'header
    """
    try:
        # Decodifica il token JWT
        payload = jwt.decode(
            token, 
            settings.csrf_secret, 
            algorithms=[settings.algorithm]
        )
        
        # Estrai il token CSRF
        csrf_token = payload.get("csrf")
        
        # Verifica che il token CSRF sia presente e corrisponda a quello nell'header
        if not csrf_token or csrf_token != header_token:
            logger.warning("CSRF token mismatch")
            return False
        
        return True
    except JWTError as e:
        logger.error(f"JWT error durante la verifica del token CSRF: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Errore generico durante la verifica del token CSRF: {str(e)}")
        return False

async def csrf_protect(
    request: Request,
    csrf_token_header: str = Depends(lambda r: r.headers.get("X-CSRF-Token")),
    csrf_token_cookie: str = Depends(csrf_cookie)
):
    """
    Middleware di protezione CSRF per route POST/PUT/DELETE
    """
    # Skip se il metodo è GET/HEAD/OPTIONS
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        return
    
    # Verifica che sia il cookie che l'header siano presenti
    if not csrf_token_cookie or not csrf_token_header:
        logger.warning("CSRF protection: missing cookie or header")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token mancante"
        )
    
    # Verifica che il token sia valido
    if not verify_csrf_token(csrf_token_cookie, csrf_token_header):
        logger.warning("CSRF protection: invalid token")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token non valido"
        )
    
    # Se arriviamo qui, il token CSRF è valido
    return True 