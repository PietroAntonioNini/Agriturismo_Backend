from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi import Request, HTTPException, Depends
import os
import logging
import time
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from app.config import settings
from app.routers import apartments, tenants, leases, utilities, auth, users
from app.database import create_tables
from app.utils.rate_limiter import limiter

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

# Configurazione API FastAPI con opzioni personalizzate per Swagger
app = FastAPI(
    title="Property Management API",
    description="API per la gestione di appartamenti in affitto",
    version="0.1.0",
    # Modifichiamo Swagger UI per renderlo più semplice
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,  # Nascondi modelli per default
        "persistAuthorization": True,    # Mantieni autorizzazione tra refresh
        "tryItOutEnabled": True,         # Abilita "Try it out" di default
        "displayRequestDuration": True,  # Mostra durata richieste
        "filter": True,                  # Abilita filtro ricerca
        "syntaxHighlight.theme": "monokai" # Tema scuro per il codice
    },
    docs_url=None,  # Disabilitiamo la documentazione standard per personalizzarla
    redoc_url="/redoc",
)

# Configurazione rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware semplice per il caching
@app.middleware("http")
async def cache_middleware(request: Request, call_next):
    # Ignora il caching se non abilitato
    if not settings.cache_enabled:
        return await call_next(request)
    
    # Cache solo per richieste GET
    if request.method != "GET":
        return await call_next(request)
    
    # Ignora caching per endpoint di autenticazione
    if "/auth/" in request.url.path:
        return await call_next(request)
    
    # Genera chiave di cache
    cache_key = f"{request.method}:{request.url.path}"
    
    # Per ora gestiamo il caching in-memory (in produzione si userebbe Redis)
    # Questo è solo un esempio dimostrativo, in produzione serve una soluzione più robusta
    if hasattr(app.state, "cache") and cache_key in app.state.cache:
        cached_response = app.state.cache[cache_key]
        if cached_response["expires"] > time.time():
            logger.debug(f"Servendo risposta da cache per {cache_key}")
            return Response(
                content=cached_response["content"],
                status_code=cached_response["status_code"],
                headers=dict(cached_response["headers"]),
                media_type=cached_response["media_type"]
            )
    
    # Esegue la richiesta originale
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    # Cache la risposta se è 2xx
    if 200 <= response.status_code < 300:
        # Copia il contenuto della risposta
        content = b""
        async for chunk in response.body_iterator:
            content += chunk
        
        # Crea cache in-memory
        if not hasattr(app.state, "cache"):
            app.state.cache = {}
        
        # Salva la risposta in cache
        app.state.cache[cache_key] = {
            "content": content,
            "status_code": response.status_code,
            "headers": list(response.headers.items()),
            "media_type": response.media_type,
            "expires": time.time() + settings.cache_expire_seconds
        }
        
        # Ricrea la risposta
        return Response(
            content=content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )
    
    return response

# Middleware per logging performance
@app.middleware("http")
async def performance_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Log solo se il tempo è significativo
    if process_time > 0.5:  # Log solo se la richiesta richiede più di 500ms
        logger.warning(f"Richiesta lenta: {request.method} {request.url.path} - {process_time:.2f}s")
    else:
        logger.debug(f"Richiesta: {request.method} {request.url.path} - {process_time:.2f}s")
    
    # Aggiungi header con il tempo di elaborazione
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Configurazione avanzata di CORS per supportare le richieste autenticate dal frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,  # 10 minuti di cache per le preflight request
)

logger.info(f"CORS configurato per domini: {settings.cors_origins}")

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(apartments.router)
app.include_router(tenants.router)
app.include_router(leases.router)
app.include_router(utilities.router)
app.include_router(auth.router)  # Authentication router
app.include_router(users.router)  # Users router

# Personalizzazione della UI Swagger per abilitare inserimento diretto del token JWT
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - API Documentation",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4.18.3/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4.18.3/swagger-ui.css",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,
            "persistAuthorization": True,
            "tryItOutEnabled": True,
            "displayRequestDuration": True,
            "syntaxHighlight.theme": "monokai",
            "docExpansion": "none",
            "filter": True,
        },
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
    )

@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    # Personalizza lo schema OpenAPI per usare ApiKey
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Aggiungi componente di sicurezza ApiKey
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Inserisci il token con prefisso: **Bearer {token}**"
        }
    }
    
    # Applica sicurezza globale
    openapi_schema["security"] = [{"ApiKeyAuth": []}]
    
    return openapi_schema

@app.get("/")
async def root():
    return {"message": "Benvenuto all'API di gestione appartamenti. Vai a /docs per la documentazione"}

@app.get("/health")
async def health_check():
    """Endpoint per verificare che l'API sia attiva e funzionante"""
    return {"status": "healthy", "version": app.version}