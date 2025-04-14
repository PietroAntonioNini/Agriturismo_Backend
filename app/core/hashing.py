from passlib.context import CryptContext
import logging

# Configurazione del logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Hasher:
    @staticmethod
    def verify_password(plain_password, hashed_password):
        """
        Verify a password against a hash
        """
        try:
            logger.info(f"Verifica password: lunghezza plain_password={len(plain_password)}, lunghezza hash={len(hashed_password)}")
            result = pwd_context.verify(plain_password, hashed_password)
            logger.info(f"Risultato verifica password: {result}")
            return result
        except Exception as e:
            logger.error(f"Errore durante la verifica password: {str(e)}")
            return False

    @staticmethod
    def get_password_hash(password):
        """
        Hash a password
        """
        try:
            logger.info(f"Generating hash for password of length {len(password)}")
            hashed = pwd_context.hash(password)
            logger.info(f"Generated hash of length {len(hashed)}")
            return hashed
        except Exception as e:
            logger.error(f"Errore durante la generazione hash: {str(e)}")
            raise e 