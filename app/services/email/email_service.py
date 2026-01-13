import logging
import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from app.config import settings
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

logger = logging.getLogger(__name__)

class EmailService:
    """
    Servizio per l'invio di email con supporto multipli provider:
    - SMTP (Gmail, Outlook, ecc.) - GRATUITO
    - SendGrid (opzionale)
    """
    
    def __init__(self):
        self.provider = settings.email_provider.lower()
        self.jinja_env = Environment(
            loader=FileSystemLoader(os.path.join(Path(__file__).parent.parent.parent, "templates/email"))
        )
        
        # Determina email mittente in base al provider
        if self.provider == "smtp":
            self.from_email = settings.from_email
            self.from_name = settings.from_name
            # Configurazione SMTP
            self.smtp_host = settings.smtp_host
            self.smtp_port = settings.smtp_port
            self.smtp_username = settings.smtp_username
            self.smtp_password = settings.smtp_password
            self.smtp_use_tls = settings.smtp_use_tls
            
            if not self.smtp_username or not self.smtp_password:
                logger.warning("SMTP username o password non configurati. L'invio email potrebbe non funzionare.")
        else:
            # SendGrid (default)
            self.from_email = settings.sendgrid_from_email
            self.from_name = settings.sendgrid_from_name
            self.api_key = settings.sendgrid_api_key
            self.sendgrid_client = None
            
            if self.api_key:
                try:
                    import sendgrid
                    from sendgrid.helpers.mail import Mail, Email, To, Content, Subject
                    self.sendgrid_client = sendgrid.SendGridAPIClient(api_key=self.api_key)
                except ImportError:
                    logger.error("SendGrid non installato. Installa con: pip install sendgrid")
                except Exception as e:
                    logger.error(f"Errore nell'inizializzazione SendGrid: {str(e)}")
            else:
                logger.warning("SendGrid API key non configurata. Email sending will be simulated.")
        
        logger.info(f"EmailService inizializzato con provider: {self.provider}")
    
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
    
    def _send_via_smtp(self, to_email, subject, html_content):
        """Invia email tramite SMTP (Gmail, Outlook, ecc.)"""
        try:
            if not self.smtp_username or not self.smtp_password:
                logger.error("SMTP username o password non configurati")
                return False
            
            # Crea il messaggio
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = Header(subject, 'utf-8')
            
            # Aggiungi contenuto HTML
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Invia via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email inviata con successo via SMTP a {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Errore autenticazione SMTP: {str(e)}")
            logger.error("Verifica che SMTP_USERNAME e SMTP_PASSWORD siano corretti")
            return False
        except Exception as e:
            logger.error(f"Errore nell'invio email via SMTP: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def _send_via_sendgrid(self, to_email, subject, html_content):
        """Invia email tramite SendGrid"""
        try:
            if not self.sendgrid_client:
                logger.error("SendGrid client non inizializzato")
                return False
            
            from sendgrid.helpers.mail import Mail, Email, To, Content, Subject
            
            from_email = Email(self.from_email, self.from_name)
            to_email_obj = To(to_email)
            subject_obj = Subject(subject)
            content = Content("text/html", html_content)
            mail = Mail(from_email, to_email_obj, subject_obj, content)
            
            response = self.sendgrid_client.send(mail)
            success = 200 <= response.status_code < 300
            
            if success:
                logger.info(f"Email inviata con successo via SendGrid a {to_email}")
            else:
                logger.error(f"Errore SendGrid: {response.status_code} - {response.body}")
            
            return success
            
        except Exception as e:
            logger.error(f"Errore nell'invio email via SendGrid: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def send_email(self, to_email, subject, template_name, context):
        """
        Invia un'email utilizzando un template HTML.
        Supporta multipli provider: SMTP, SendGrid
        """
        try:
            # Renderizza il template HTML
            html_content = self._render_template(template_name, context)
            
            # Invia tramite il provider configurato
            if self.provider == "smtp":
                return self._send_via_smtp(to_email, subject, html_content)
            elif self.provider == "sendgrid":
                return self._send_via_sendgrid(to_email, subject, html_content)
            else:
                logger.error(f"Provider email sconosciuto: {self.provider}")
                logger.error("Provider supportati: smtp, sendgrid")
                return False
                
        except Exception as e:
            logger.error(f"Errore nell'invio email: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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
