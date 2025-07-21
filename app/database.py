from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import logging
from sqlalchemy.exc import ProgrammingError

from app.config import settings

logger = logging.getLogger(__name__)

def create_database_if_not_exists(url):
    db_name = url.split('/')[-1]
    base_url = '/'.join(url.split('/')[:-1] + ['postgres']) # Connect to default 'postgres' db

    # Create engine with autocommit isolation level
    temp_engine = create_engine(base_url, isolation_level="AUTOCOMMIT")
    
    try:
        with temp_engine.connect() as conn:
            # Check if database exists
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": db_name}
            ).scalar()
            
            if not exists:
                # Create database if it doesn't exist
                conn.execute(text(f"CREATE DATABASE {db_name}"))
                logger.info(f"Database {db_name} creato con successo")
            else:
                logger.info(f"Database {db_name} già esistente")
                
    except ProgrammingError as e:
        # Handle potential race condition or permission issues gracefully
        logger.warning(f"Could not create database {db_name}. It might already exist or check permissions. Error: {e}")
    except Exception as e:
        logger.error(f"Errore durante la verifica/creazione del database: {str(e)}")
        raise
    finally:
        temp_engine.dispose()

# Normalizza l'URL del database per SQLAlchemy
def normalize_database_url(url: str) -> str:
    """Converte postgres:// in postgresql:// per compatibilità SQLAlchemy"""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url

# Create database if not exists (only if using postgres)
if "postgres" in settings.database_url:
    try:
        create_database_if_not_exists(settings.database_url)
    except Exception as e:
        logger.error(f"Errore durante l'inizializzazione del database: {str(e)}")
        # Decide if you want to raise the error or just log it and continue
        # raise # Uncomment to stop the application if DB check/creation fails
else:
    logger.info("Skipping PostgreSQL database check/creation for non-PostgreSQL URL.")


# Create the main database engine for the application using the URL from settings
normalized_url = normalize_database_url(settings.database_url)
engine = create_engine(
    normalized_url,
    connect_args={"check_same_thread": False} if "sqlite" in normalized_url else {},
    # Il parametro isolation_level va FUORI da connect_args
    isolation_level="READ COMMITTED" if "postgresql" in normalized_url else "SERIALIZABLE",
    pool_pre_ping=True,
    pool_recycle=3600
)

# Modificare SessionLocal per ottimizzare la gestione delle transazioni
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=True,  # Cambiato da False a True 
    bind=engine
)

# Create Base class
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to create all tables
def create_tables():
    import app.models.models
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tabelle create/verificate con successo nel database.")
    except Exception as e:
        logger.error(f"Errore durante la creazione delle tabelle: {e}")
        raise