from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.config import settings
from app.routers import apartments, tenants, leases, utilities
from app.database import engine, Base

# Creazione delle tabelle nel database
Base.metadata.create_all(bind=engine)

# Crea directory statica se non esiste
os.makedirs("static/apartments", exist_ok=True)
os.makedirs("static/tenants", exist_ok=True)
os.makedirs("static/leases", exist_ok=True)

app = FastAPI(
    title="Property Management API",
    description="API per la gestione di appartamenti in affitto",
    version="0.1.0",
)

# Configurazione CORS per permettere le richieste dal frontend Angular
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve i file statici
app.mount("/static", StaticFiles(directory="static"), name="static")

# Inclusione dei router
app.include_router(apartments.router)
app.include_router(tenants.router)
app.include_router(leases.router)
app.include_router(utilities.router)

@app.get("/")
async def root():
    return {"message": "Benvenuto all'API di gestione appartamenti. Vai a /docs per la documentazione"}