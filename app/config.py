import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import logging
import secrets

load_dotenv()

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    app_name: str = "FastAPI Backend"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    secret_key: str = os.getenv("SECRET_KEY", "una_chiave_segreta_predefinita")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    # Token settings
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    # Rate limiting settings
    rate_limit_login: str = os.getenv("RATE_LIMIT_LOGIN", "5/minute")
    rate_limit_register: str = os.getenv("RATE_LIMIT_REGISTER", "3/minute")
    rate_limit_default: str = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")
    # Configurazioni CORS per l'integrazione con il frontend
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200,http://localhost:4000,http://127.0.0.1:4000")
    
    @property
    def cors_origins_list(self) -> list:
        """Converte la stringa CORS_ORIGINS in una lista"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    # Configurazioni per l'upload dei file
    max_upload_size: int = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB di default
    allowed_upload_extensions: list = os.getenv("ALLOWED_UPLOAD_EXTENSIONS", ".jpg,.jpeg,.png,.pdf,.doc,.docx").split(",")
    # Configurazioni per la sicurezza
    password_min_length: int = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
    password_require_uppercase: bool = os.getenv("PASSWORD_REQUIRE_UPPERCASE", "True").lower() == "true"
    password_require_lowercase: bool = os.getenv("PASSWORD_REQUIRE_LOWERCASE", "True").lower() == "true"
    password_require_digit: bool = os.getenv("PASSWORD_REQUIRE_DIGIT", "True").lower() == "true"
    password_require_special: bool = os.getenv("PASSWORD_REQUIRE_SPECIAL", "True").lower() == "true"
    # Configurazioni per caching
    cache_enabled: bool = os.getenv("CACHE_ENABLED", "True").lower() == "true"
    cache_expire_seconds: int = int(os.getenv("CACHE_EXPIRE_SECONDS", "60"))
    # Security settings
    csrf_secret: str = os.getenv("CSRF_SECRET", secrets.token_hex(32))
    csrf_token_expire_minutes: int = int(os.getenv("CSRF_TOKEN_EXPIRE_MINUTES", "60"))
    enable_ssl_redirect: bool = os.getenv("ENABLE_SSL_REDIRECT", "False").lower() == "true"
    # Email settings
    sendgrid_api_key: str = os.getenv("SENDGRID_API_KEY", "")
    sendgrid_from_email: str = os.getenv("SENDGRID_FROM_EMAIL", "no-reply@agriturismo.com")
    sendgrid_from_name: str = os.getenv("SENDGRID_FROM_NAME", "Agriturismo Support")
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:4200")
    # Password reset settings
    password_reset_token_expire_hours: int = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_HOURS", "24"))
    # Configurazioni per rate limiting specifici per reset password
    rate_limit_forgot_password: str = os.getenv("RATE_LIMIT_FORGOT_PASSWORD", "3/hour")

settings = Settings()

logger.info(f"Configurazione caricata: DB={settings.database_url}, TokenExpire={settings.access_token_expire_minutes}m, RefreshExpire={settings.refresh_token_expire_days}d")