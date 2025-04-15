import secrets
import string
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.models import PasswordResetToken, User
from app.config import settings

class TokenService:
    """
    Servizio per la gestione dei token di sicurezza.
    Genera, verifica e invalida token per operazioni come reset password e verifica account.
    """
    
    @staticmethod
    def generate_secure_token(length=64):
        """
        Genera un token sicuro casuale.
        
        Args:
            length: Lunghezza del token (default: 64 caratteri)
            
        Returns:
            str: Token generato
        """
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def create_password_reset_token(db: Session, user: User):
        """
        Crea un token di reset password e lo salva nel database.
        Invalida eventuali token precedenti per lo stesso utente.
        
        Args:
            db: Sessione del database
            user: Utente per cui generare il token
            
        Returns:
            str: Token generato
        """
        # Invalida eventuali token esistenti per l'utente
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.is_used == False,
            PasswordResetToken.expires > datetime.utcnow()
        ).update({"is_used": True, "used_at": datetime.utcnow()})
        
        # Genera un nuovo token
        token_value = TokenService.generate_secure_token()
        token = PasswordResetToken(
            token=token_value,
            user_id=user.id,
            expires=datetime.utcnow() + timedelta(hours=settings.password_reset_token_expire_hours),
            is_used=False
        )
        
        # Salva nel database
        db.add(token)
        db.commit()
        db.refresh(token)
        
        return token_value
    
    @staticmethod
    def validate_reset_token(db: Session, token_value: str):
        """
        Verifica se un token di reset è valido.
        
        Args:
            db: Sessione del database
            token_value: Valore del token da verificare
            
        Returns:
            PasswordResetToken|None: Oggetto token se valido, None altrimenti
        """
        token = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == token_value,
            PasswordResetToken.is_used == False,
            PasswordResetToken.expires > datetime.utcnow()
        ).first()
        
        return token
    
    @staticmethod
    def invalidate_token(db: Session, token: PasswordResetToken):
        """
        Invalida un token dopo l'utilizzo.
        
        Args:
            db: Sessione del database
            token: Token da invalidare
        """
        token.is_used = True
        token.used_at = datetime.utcnow()
        db.commit()
    
    @staticmethod
    def purge_expired_tokens(db: Session):
        """
        Elimina i token scaduti dal database.
        Utile per operazioni di manutenzione periodica.
        
        Args:
            db: Sessione del database
            
        Returns:
            int: Numero di token eliminati
        """
        # Trova tutti i token scaduti
        result = db.query(PasswordResetToken).filter(
            PasswordResetToken.expires < datetime.utcnow()
        ).delete()
        
        db.commit()
        return result 