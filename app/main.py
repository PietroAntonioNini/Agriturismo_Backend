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
from starlette.responses import RedirectResponse

from app.config import settings
from app.routers import apartments, tenants, leases, utilities, auth, users
from app.routers import settings as settings_router
logger = logging.getLogger(__name__)

# Debug import invoices
try:
    logger.info("Tentativo di import del router invoices...")
    from app.routers import invoices
    logger.info("✅ Router invoices importato con successo!")
except Exception as e:
    logger.error(f"❌ Errore nell'import del router invoices: {e}")
    import traceback
    logger.error(f"Traceback completo: {traceback.format_exc()}")
    # Crea un router vuoto per evitare errori
    from fastapi import APIRouter
    invoices = type('MockInvoices', (), {'router': APIRouter()})()


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
    redirect_slashes=False,  # Disabilita redirect automatico per trailing slash
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
    
    # Ignora caching per endpoint di autenticazione e utenti
    if "/auth/" in request.url.path or "/users/" in request.url.path:
        return await call_next(request)
    
    # DISABILITA COMPLETAMENTE LA CACHE PER RICHIESTE AUTENTICATE
    # Questo risolve il problema di sincronizzazione tra frontend e backend
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return await call_next(request)
    
    # Ignora crawler e bot
    user_agent = request.headers.get("User-Agent", "").lower()
    bot_patterns = ["bot", "crawler", "spider", "slurp", "baiduspider", "yandex"]
    if any(pattern in user_agent for pattern in bot_patterns):
        return await call_next(request)
    
    # Genera chiave di cache
    cache_key = f"{request.method}:{request.url.path}:{request.query_params}"
    
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

# Middleware per invalidare la cache quando vengono fatte modifiche
@app.middleware("http")
async def cache_invalidation_middleware(request: Request, call_next):
    # Esegue la richiesta originale
    response = await call_next(request)
    
    # Se la richiesta è stata completata con successo (2xx) e è una modifica
    if 200 <= response.status_code < 300 and request.method in ["PUT", "POST", "DELETE", "PATCH"]:
        # Invalida la cache per le risorse modificate
        if hasattr(app.state, "cache") and app.state.cache:
            path = request.url.path
            
            # Lista delle chiavi da invalidare
            keys_to_remove = []
            
            # Invalida cache per tenant
            if "/tenants/" in path:
                # Invalida tutte le cache relative ai tenant
                for cache_key in app.state.cache.keys():
                    if "GET:/tenants/" in cache_key:
                        keys_to_remove.append(cache_key)
                        logger.debug(f"Invalidando cache per tenant: {cache_key}")
            
            # Invalida cache per appartamenti
            elif "/apartments/" in path:
                # Invalida tutte le cache relative agli appartamenti
                for cache_key in app.state.cache.keys():
                    if "GET:/apartments/" in cache_key:
                        keys_to_remove.append(cache_key)
                        logger.debug(f"Invalidando cache per appartamento: {cache_key}")
            
            # Invalida cache per contratti
            elif "/leases/" in path:
                # Invalida tutte le cache relative ai contratti
                for cache_key in app.state.cache.keys():
                    if "GET:/leases/" in cache_key:
                        keys_to_remove.append(cache_key)
                        logger.debug(f"Invalidando cache per contratto: {cache_key}")
            
            # Invalida cache per utilities
            elif "/utilities/" in path:
                # Invalida tutte le cache relative alle utilities
                for cache_key in app.state.cache.keys():
                    if "GET:/utilities/" in cache_key:
                        keys_to_remove.append(cache_key)
                        logger.debug(f"Invalidando cache per utility: {cache_key}")
            
            # Rimuovi le chiavi dalla cache
            for key in keys_to_remove:
                app.state.cache.pop(key, None)
            
            if keys_to_remove:
                logger.info(f"Invalidate {len(keys_to_remove)} chiavi di cache per {path}")
    
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

# Middleware per aggiungere security headers
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    
    # Strict-Transport-Security: indica al browser di usare sempre HTTPS
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Cache-Control: previene il caching lato browser per tutte le API scoped all'utente
    # Questi endpoint ritornano dati diversi a seconda dell'utente autenticato
    user_scoped_paths = [
        "/api/",
        "/tenants/",
        "/apartments/",
        "/leases/",
        "/utilities/",
        "/invoices/",
        "/users/",
        "/maintenance/"
    ]
    
    # Se è un endpoint scoped all'utente, disabilita il caching
    if any(request.url.path.startswith(path) for path in user_scoped_paths):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, private, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["Vary"] = "Authorization"  # Fondamentale per HTTP caching proxies
        # Forza il browser a non cachare e a rivalidare sempre
        response.headers["ETag"] = ""  # Rimuovi ETag per forzare la revalidazione
    
    # Headers per auth endpoints - molto importante che non vengano mai cachati
    if "/auth/" in request.url.path or "/login" in request.url.path or "/logout" in request.url.path:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, private, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["Vary"] = "Authorization"
    
    # X-Content-Type-Options: previene MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # X-Frame-Options: previene clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    
    # X-XSS-Protection: abilita protezione XSS nel browser
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Content-Security-Policy
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:;"
    
    return response

# Middleware per reindirizzare HTTP a HTTPS in produzione
@app.middleware("http")
async def https_redirect_middleware(request: Request, call_next):
    # Controlla se il redirect è abilitato nelle impostazioni
    if not settings.enable_ssl_redirect:
        return await call_next(request)
    
    # Controlla se la richiesta è già HTTPS
    if request.url.scheme == "https":
        return await call_next(request)
    
    # In produzione, X-Forwarded-Proto potrebbe essere impostato dal load balancer
    forwarded_proto = request.headers.get("X-Forwarded-Proto")
    if forwarded_proto == "https":
        return await call_next(request)
    
    # Controlla se è una richiesta API (non reindirizzare le API)
    api_paths = [
        "/api/", "/auth/", "/apartments/", "/tenants/",
        "/leases/", "/utilities/", "/users/", "/health"
    ]
    if any(request.url.path.startswith(path) for path in api_paths):
        return await call_next(request)
    
    # Reindirizza a HTTPS solo per le pagine web
    https_url = str(request.url).replace("http://", "https://", 1)
    return RedirectResponse(https_url, status_code=HTTP_429_TOO_MANY_REQUESTS)

# Configurazione avanzata di CORS per supportare le richieste autenticate dal frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,  # 10 minuti di cache per le preflight request
)

logger.info(f"CORS configurato per domini: {settings.cors_origins_list}")

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
logger.info("Registrazione router apartments...")
app.include_router(apartments.router)
logger.info("Registrazione router tenants...")
app.include_router(tenants.router)
logger.info("Registrazione router leases...")
app.include_router(leases.router)
logger.info("Registrazione router utilities...")
app.include_router(utilities.router)
logger.info("Registrazione router invoices...")
app.include_router(invoices.router)  # Invoices router
logger.info("Registrazione router auth...")
app.include_router(auth.router)  # Authentication router
logger.info("Registrazione router users...")
app.include_router(users.router)  # Users router
logger.info("Registrazione router settings...")
app.include_router(settings_router.router)  # Settings router
logger.info("Registrazione router settings (compat /api)...")
app.include_router(settings_router.router, prefix="/api")  # Compatibilità con chiamate /api/settings
logger.info("✅ Tutti i router registrati con successo!")

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

@app.get("/debug/routes")
async def debug_routes():
    """Endpoint per il debug che mostra tutti gli endpoint disponibili dell'API."""
    routes = []
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": getattr(route, "name", "N/A")
            })
    return {"routes": routes}

@app.post("/debug/clear-cache")
async def clear_cache():
    """Endpoint per pulire manualmente la cache."""
    if hasattr(app.state, "cache"):
        cache_size = len(app.state.cache)
        app.state.cache.clear()
        logger.info(f"Cache pulita manualmente. Rimossi {cache_size} elementi.")
        return {"message": f"Cache pulita. Rimossi {cache_size} elementi."}
    else:
        return {"message": "Nessuna cache da pulire."}

@app.get("/debug/cache-stats")
async def cache_stats():
    """Endpoint per visualizzare le statistiche della cache."""
    if hasattr(app.state, "cache"):
        cache_size = len(app.state.cache)
        cache_keys = list(app.state.cache.keys())
        return {
            "cache_enabled": settings.cache_enabled,
            "cache_size": cache_size,
            "cache_expire_seconds": settings.cache_expire_seconds,
            "cache_keys": cache_keys
        }
    else:
        return {
            "cache_enabled": settings.cache_enabled,
            "cache_size": 0,
            "cache_expire_seconds": settings.cache_expire_seconds,
            "cache_keys": []
        }