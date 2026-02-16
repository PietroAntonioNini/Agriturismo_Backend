
import os
import boto3
from botocore.exceptions import ClientError
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class R2Manager:
    def __init__(self):
        # Inizializza il client S3 usando i segreti di Koyeb/Config
        self.s3 = boto3.client(
            service_name='s3',
            endpoint_url=settings.r2_endpoint_url,
            aws_access_key_id=settings.r2_access_key,
            aws_secret_access_key=settings.r2_secret_key,
            region_name='auto' # R2 richiede 'auto'
        )

    def upload_file(self, file_content, file_name, file_type):
        """
        Carica il file nel bucket corrispondente.
        file_type: 'prospetto', 'contratto' o 'documento'
        """
        # Mappatura dei bucket dalle variabili d'ambiente
        bucket_map = {
            'prospetto': settings.bucket_prospetti,
            'contratto': settings.bucket_contratti,
            'documento': settings.bucket_documenti_inquilini
        }

        target_bucket = bucket_map.get(file_type)
        if not target_bucket:
            logger.error(f"Tipo file '{file_type}' non valido o bucket non configurato.")
            # raise ValueError(f"Tipo file '{file_type}' non valido o bucket non configurato") # Optional: raise or return False
            return False

        try:
            content_type = 'application/pdf' if file_name.lower().endswith('.pdf') else 'application/octet-stream'
            # Detect basic image types too if needed, but PDF is primary use case from description
            if file_name.lower().endswith('.jpg') or file_name.lower().endswith('.jpeg'):
                content_type = 'image/jpeg'
            elif file_name.lower().endswith('.png'):
                content_type = 'image/png'

            self.s3.put_object(
                Bucket=target_bucket,
                Key=file_name,
                Body=file_content,
                ContentType=content_type
            )
            return True
        except ClientError as e:
            logger.error(f"Errore R2 Upload nel bucket '{target_bucket}': {e}")
            logger.error(f"Dettagli errore: {e.response if hasattr(e, 'response') else 'Nessun dettaglio'}")
            return False
        except Exception as e:
            logger.error(f"Errore generico in R2 Upload: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def get_signed_url(self, file_key, file_type, expires_in=3600):
        """
        Genera un link temporaneo (1 ora) per visualizzare il file nella Web App.
        Fondamentale per la privacy dei contratti e delle carte d'identità.
        """
        bucket_map = {
            'prospetto': settings.bucket_prospetti,
            'contratto': settings.bucket_contratti,
            'documento': settings.bucket_documenti_inquilini
        }
        
        target_bucket = bucket_map.get(file_type)
        if not target_bucket:
            return None

        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': target_bucket, 'Key': file_key},
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            logger.error(f"Errore generazione URL: {e}")
            return None
