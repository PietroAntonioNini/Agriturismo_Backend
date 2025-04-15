import logging
import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from app.config import settings
from pathlib import Path
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content, Subject

logger = logging.getLogger(__name__)

class EmailService:
    """
    Servizio per l'invio di email utilizzando SendGrid.
    
    Nota: Questo servizio richiede la configurazione di SendGrid.
    Prima di utilizzarlo in produzione:
    1. Registrarsi su SendGrid e ottenere una API key
    2. Configurare le variabili d'ambiente in .env
    3. Configurare i DNS per il dominio mittente
    """
    
    def __init__(self):
        self.api_key = settings.sendgrid_api_key
        self.from_email = settings.sendgrid_from_email
        self.from_name = settings.sendgrid_from_name
        self.client = None
        self.jinja_env = Environment(
            loader=FileSystemLoader(os.path.join(Path(__file__).parent.parent.parent, "templates/email"))
        )
        
        # Se l'API key è presente, inizializza il client
        if self.api_key:
            self.client = sendgrid.SendGridAPIClient(api_key=self.api_key)
        else:
            logger.warning("SendGrid API key not configured. Email sending will be simulated.")
    
    def _render_template(self, template_name, context):
        """Renderizza un template HTML con Jinja2"""
        try:
            template = self.jinja_env.get_template(f"{template_name}.html")
            # Aggiungi l'anno corrente al contesto per il copyright nel footer
            context['current_year'] = datetime.now().year
            return template.render(**context)
        except Exception as e:
            logger.error(f"Error rendering email template {template_name}: {str(e)}")
            # Fallback a un messaggio semplice in caso di errore
            return f"<p>Messaggio dal sistema</p><p>{context.get('message', '')}</p>"
    
    def send_email(self, to_email, subject, template_name, context):
        """
        Invia un'email utilizzando un template HTML.
        
        Args:
            to_email: Indirizzo email del destinatario
            subject: Oggetto dell'email
            template_name: Nome del template (senza estensione .html)
            context: Dizionario con le variabili per il template
        
        Returns:
            bool: True se l'invio è riuscito, False altrimenti
        """
        try:
            # Renderizza il template HTML
            html_content = self._render_template(template_name, context)
            
            # Crea il messaggio
            from_email = Email(self.from_email, self.from_name)
            to_email = To(to_email)
            subject = Subject(subject)
            content = Content("text/html", html_content)
            mail = Mail(from_email, to_email, subject, content)
            
            # Invia l'email se il client è configurato
            if self.client:
                response = self.client.client.mail.send.post(request_body=mail.get())
                success = 200 <= response.status_code < 300
                
                if success:
                    logger.info(f"Email sent successfully to {to_email}")
                else:
                    logger.error(f"Failed to send email: {response.status_code} - {response.body}")
                
                return success
            else:
                # Modalità simulazione (per sviluppo/testing)
                logger.info(f"SIMULATION: Email would be sent to {to_email}")
                logger.info(f"SIMULATION: Subject: {subject}")
                logger.info(f"SIMULATION: Content: {html_content[:100]}...")
                return True
        
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    def send_password_reset_email(self, user, reset_token):
        """
        Invia un'email per il reset della password.
        
        Args:
            user: L'utente che ha richiesto il reset
            reset_token: Il token di reset generato
        
        Returns:
            bool: True se l'invio è riuscito, False altrimenti
        """
        # Costruisci l'URL completo per il reset
        reset_url = f"{settings.frontend_url}/auth/reset-password?token={reset_token}"
        
        # Prepara il contesto per il template
        context = {
            "user": user,
            "reset_token": reset_token,
            "reset_url": reset_url,
            "expiry_hours": settings.password_reset_token_expire_hours
        }
        
        # Invia l'email
        return self.send_email(
            user.email,
            "Richiesta di Reset Password - Agriturismo",
            "password_reset",
            context
        )
    
    def send_security_notification_email(self, user, activity_type, ip_address=None, user_agent=None):
        """
        Invia una notifica di sicurezza all'utente.
        
        Args:
            user: L'utente da notificare
            activity_type: Tipo di attività (es. "Reset Password", "Login")
            ip_address: Indirizzo IP da cui è stata effettuata l'attività
            user_agent: User agent del browser
        
        Returns:
            bool: True se l'invio è riuscito, False altrimenti
        """
        context = {
            "user": user,
            "activity_type": activity_type,
            "ip_address": ip_address or "Non disponibile",
            "user_agent": user_agent or "Non disponibile",
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
        
        return self.send_email(
            user.email,
            f"Notifica di Sicurezza - {activity_type} - Agriturismo",
            "security_notification",
            context
        )
    
    def send_account_verification_email(self, user, verification_token):
        """
        Invia un'email per la verifica dell'account.
        
        Args:
            user: L'utente che deve verificare l'account
            verification_token: Il token di verifica generato
        
        Returns:
            bool: True se l'invio è riuscito, False altrimenti
        """
        # Costruisci l'URL completo per la verifica
        verification_url = f"{settings.frontend_url}/auth/verify-account?token={verification_token}"
        
        context = {
            "user": user,
            "verification_token": verification_token,
            "verification_url": verification_url,
            "expiry_hours": 48  # Durata predefinita per la verifica
        }
        
        return self.send_email(
            user.email,
            "Verifica il tuo account - Agriturismo",
            "account_verification",
            context
        ) 