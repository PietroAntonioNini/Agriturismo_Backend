# API di Gestione Appartamenti

API backend per la gestione di appartamenti, inquilini e contratti di affitto.

## Sicurezza API

Questo backend implementa diverse misure di sicurezza avanzate:

### 1. CORS (Cross-Origin Resource Sharing)

Il backend è configurato per accettare richieste solo da domini specifici, configurabili tramite la variabile d'ambiente `CORS_ORIGINS`.

### 2. Security Headers

Ogni risposta include i seguenti header di sicurezza:
- `Strict-Transport-Security`: Forza HTTPS
- `Content-Security-Policy`: Previene attacchi XSS
- `X-Content-Type-Options`: Previene il MIME sniffing
- `X-Frame-Options`: Protegge dal clickjacking
- `X-XSS-Protection`: Protezione XSS aggiuntiva
- `Referrer-Policy`: Limita le informazioni passate tramite header referer
- `Permissions-Policy`: Controlla l'accesso alle API del browser

### 3. Protezione CSRF

Il backend implementa protezione CSRF per le operazioni di modifica (POST/PUT/DELETE).

#### Uso lato client:

1. Ottieni un token CSRF:
```javascript
// Recupera il token CSRF
const response = await fetch('/api/auth/csrf-token');
const { csrf_token } = await response.json();

// Salva il token (il cookie sarà impostato automaticamente)
localStorage.setItem('csrfToken', csrf_token);
```

2. Includi il token nelle richieste di modifica:
```javascript
const response = await fetch('/api/some-endpoint', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRF-Token': localStorage.getItem('csrfToken')
  },
  body: JSON.stringify(data)
});
```

### 4. Rate Limiting

Il backend implementa limiti di richieste per prevenire attacchi di forza bruta:
- Login: 5 tentativi al minuto
- Registrazione: 3 tentativi al minuto
- API generiche: 60 richieste al minuto

### 5. Autenticazione JWT

L'API utilizza:
- Access token JWT con scadenza configurabile
- Refresh token con persistenza nel database
- Possibilità di logout da tutti i dispositivi

### 6. Configurazioni di Sicurezza

Le configurazioni di sicurezza sono personalizzabili tramite variabili d'ambiente:
- `ENABLE_SSL_REDIRECT`: Abilita il redirect automatico da HTTP a HTTPS
- `CSRF_SECRET`: Chiave segreta per firmare i token CSRF
- `CSRF_TOKEN_EXPIRE_MINUTES`: Durata di validità dei token CSRF

## Guida all'Uso

Vedi [Documentazione API](/docs) per informazioni dettagliate sugli endpoint disponibili.
