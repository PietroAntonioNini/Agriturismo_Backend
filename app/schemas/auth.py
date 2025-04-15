from typing import Optional
from pydantic import BaseModel, validator

class ForgotPasswordRequest(BaseModel):
    """
    Schema per la richiesta di reset password.
    Richiede almeno uno tra username ed email.
    """
    username: Optional[str] = None
    email: Optional[str] = None
    
    @validator('username', 'email')
    def check_at_least_one_field(cls, v, values):
        if not v and not values.get('username') and not values.get('email'):
            raise ValueError('Almeno uno tra username ed email deve essere fornito')
        return v

class ResetPasswordRequest(BaseModel):
    """
    Schema per il reset della password.
    """
    token: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        # Verifica della complessità della password (implementare qui o usare una funzione di utilità)
        if len(v) < 8:
            raise ValueError('La password deve essere di almeno 8 caratteri')
        # Altre verifiche di sicurezza...
        return v

class GenericResponse(BaseModel):
    """
    Schema per risposte generiche dal server.
    """
    message: str 