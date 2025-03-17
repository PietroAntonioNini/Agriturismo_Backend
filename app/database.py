from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database

from app.config import settings

SQLALCHEMY_DATABASE_URL = settings.database_url

# Crea il motore del database con le opzioni appropriate
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # 'check_same_thread' è necessario solo per SQLite
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
)

# Se stiamo usando PostgreSQL, verifica che il database esista
if not SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    if not database_exists(engine.url):
        create_database(engine.url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()