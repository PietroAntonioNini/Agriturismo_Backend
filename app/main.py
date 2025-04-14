from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import logging

from app.config import settings
from app.routers import apartments, tenants, leases, utilities, auth, users
from app.database import create_tables

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crea le tabelle del database se non esistono
logger.info("Inizializzazione del database...")
create_tables()
logger.info("Tabelle del database create/aggiornate con successo!")

# Create static directories if they don't exist
os.makedirs("static/apartments", exist_ok=True)
os.makedirs("static/tenants", exist_ok=True)
os.makedirs("static/leases", exist_ok=True)

app = FastAPI(
    title="Property Management API",
    description="API per la gestione di appartamenti in affitto",
    version="0.1.0",
)

# Configure CORS to allow requests from the Angular frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(apartments.router)
app.include_router(tenants.router)
app.include_router(leases.router)
app.include_router(utilities.router)
app.include_router(auth.router)  # Authentication router
app.include_router(users.router)  # Users router

@app.get("/")
async def root():
    return {"message": "Benvenuto all'API di gestione appartamenti. Vai a /docs per la documentazione"}