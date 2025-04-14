import logging
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

# Configurazione logging
logger = logging.getLogger(__name__)

# Configurazione del rate limiter
limiter = Limiter(key_func=get_remote_address)

# Funzione personalizzata per ottenere la chiave basata su utente o IP
def get_identifier(request: Request) -> str:
    # Se l'utente è autenticato, usa il suo username
    if hasattr(request.state, "user") and request.state.user:
        identifier = f"user:{request.state.user.username}"
        logger.debug(f"Rate limit key: {identifier}")
        return identifier
    
    # Altrimenti usa l'indirizzo IP
    ip = get_remote_address(request)
    logger.debug(f"Rate limit key (IP): {ip}")
    return f"ip:{ip}" 