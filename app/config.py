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
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Fix per Koyeb: converti postgres:// in postgresql://
        if self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql://", 1)
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
    
    # Email provider (smtp, sendgrid)
    email_provider: str = os.getenv("EMAIL_PROVIDER", "sendgrid")
    
    # SMTP settings (per Gmail, Outlook, ecc.)
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "True").lower() == "true"
    
    # Email comune (usato per SMTP e SendGrid)
    from_email: str = os.getenv("FROM_EMAIL", sendgrid_from_email)
    from_name: str = os.getenv("FROM_NAME", sendgrid_from_name)
    
    # Password reset settings
    password_reset_token_expire_hours: int = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_HOURS", "24"))
    # Configurazioni per rate limiting specifici per reset password
    rate_limit_forgot_password: str = os.getenv("RATE_LIMIT_FORGOT_PASSWORD", "3/hour")
    
    # Configurazioni per il sistema di fatturazione
    invoice_prefix: str = os.getenv("INVOICE_PREFIX", "INV")
    invoice_start_number: int = int(os.getenv("INVOICE_START_NUMBER", "1"))
    default_tax_rate: float = float(os.getenv("DEFAULT_TAX_RATE", "22.00"))
    default_due_days: int = int(os.getenv("DEFAULT_DUE_DAYS", "30"))
    default_payment_method: str = os.getenv("DEFAULT_PAYMENT_METHOD", "bank_transfer")
    
    # Configurazioni aziendali per fatture
    company_name: str = os.getenv("COMPANY_NAME", "Agriturismo Manager")
    company_address: str = os.getenv("COMPANY_ADDRESS", "Via delle Rose, 123")
    company_city: str = os.getenv("COMPANY_CITY", "12345 Città, Italia")
    company_phone: str = os.getenv("COMPANY_PHONE", "+39 123 456 7890")
    company_email: str = os.getenv("COMPANY_EMAIL", "info@agriturismo.it")
    company_iban: str = os.getenv("COMPANY_IBAN", "IT60 X054 2811 1010 0000 0123 456")
    company_vat_number: str = os.getenv("COMPANY_VAT_NUMBER", "12345678901")
    company_logo_url: str = os.getenv("COMPANY_LOGO_URL", "https://example.com/logo.png")
    
    # Configurazioni costi utility
    electricity_cost_per_kwh: float = float(os.getenv("ELECTRICITY_COST_PER_KWH", "0.25"))
    water_cost_per_m3: float = float(os.getenv("WATER_COST_PER_M3", "1.50"))
    gas_cost_per_m3: float = float(os.getenv("GAS_COST_PER_M3", "0.80"))
    
    # Configurazioni notifiche
    default_reminder_days: int = int(os.getenv("DEFAULT_REMINDER_DAYS", "7"))
    overdue_reminder_days: int = int(os.getenv("OVERDUE_REMINDER_DAYS", "3"))
    auto_send_reminders: bool = os.getenv("AUTO_SEND_REMINDERS", "True").lower() == "true"
    whatsapp_notifications_enabled: bool = os.getenv("WHATSAPP_NOTIFICATIONS_ENABLED", "True").lower() == "true"
    email_notifications_enabled: bool = os.getenv("EMAIL_NOTIFICATIONS_ENABLED", "True").lower() == "true"
    
    # Configurazioni PDF
    pdf_storage_path: str = os.getenv("PDF_STORAGE_PATH", "/storage/invoices")
    pdf_template_path: str = os.getenv("PDF_TEMPLATE_PATH", "/resources/templates/invoice")
    include_qr_code: bool = os.getenv("INCLUDE_QR_CODE", "True").lower() == "true"
    include_payment_instructions: bool = os.getenv("INCLUDE_PAYMENT_INSTRUCTIONS", "True").lower() == "true"

settings = Settings()

logger.info(f"Configurazione caricata: DB={settings.database_url}, TokenExpire={settings.access_token_expire_minutes}m, RefreshExpire={settings.refresh_token_expire_days}d")