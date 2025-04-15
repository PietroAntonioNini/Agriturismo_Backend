"""
Funzioni di utilità per la sicurezza e la gestione delle password
"""
import re
from app.config import settings
from app.core.hashing import Hasher
from fastapi import HTTPException, status

def is_password_valid(password: str) -> bool:
    """
    Verifica se una password rispetta i requisiti di sicurezza.
    
    Args:
        password: La password da verificare
        
    Returns:
        bool: True se la password è valida, False altrimenti
    """
    if len(password) < settings.password_min_length:
        return False
    
    # Verifica maiuscole
    if settings.password_require_uppercase and not any(c.isupper() for c in password):
        return False
    
    # Verifica minuscole
    if settings.password_require_lowercase and not any(c.islower() for c in password):
        return False
    
    # Verifica numeri
    if settings.password_require_digit and not any(c.isdigit() for c in password):
        return False
    
    # Verifica caratteri speciali
    if settings.password_require_special and not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'"\\|,.<>\/?]', password):
        return False
    
    return True

def validate_password_with_exception(password: str) -> None:
    """
    Verifica la password e solleva un'eccezione con dettagli specifici se non è valida.
    
    Args:
        password: La password da verificare
        
    Raises:
        HTTPException: Se la password non rispetta i requisiti
    """
    errors = []
    
    # Verifica lunghezza minima
    if len(password) < settings.password_min_length:
        errors.append(f"Password deve essere di almeno {settings.password_min_length} caratteri")
    
    # Verifica maiuscole
    if settings.password_require_uppercase and not any(c.isupper() for c in password):
        errors.append("Password deve contenere almeno una lettera maiuscola")
    
    # Verifica minuscole
    if settings.password_require_lowercase and not any(c.islower() for c in password):
        errors.append("Password deve contenere almeno una lettera minuscola")
    
    # Verifica numeri
    if settings.password_require_digit and not any(c.isdigit() for c in password):
        errors.append("Password deve contenere almeno un numero")
    
    # Verifica caratteri speciali
    if settings.password_require_special and not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'"\\|,.<>\/?]', password):
        errors.append("Password deve contenere almeno un carattere speciale")
    
    # Se ci sono errori, solleva eccezione
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Password non valida", "errors": errors}
        )

def get_password_hash(password: str) -> str:
    """
    Genera l'hash di una password utilizzando il sistema di hashing dell'applicazione.
    
    Args:
        password: La password in chiaro
        
    Returns:
        str: L'hash della password
    """
    return Hasher.get_password_hash(password) 