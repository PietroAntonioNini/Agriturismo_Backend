# 🚀 Guida Deploy su Koyeb

Questa guida ti aiuta a deployare il backend FastAPI su Koyeb, una piattaforma gratuita con PostgreSQL incluso.

## 📋 Prerequisiti

1. **Account Koyeb**: Registrati su [koyeb.com](https://koyeb.com)
2. **Docker**: Installa [Docker Desktop](https://www.docker.com/products/docker-desktop/)
3. **Git**: Assicurati che il progetto sia su GitHub

## 🔧 Configurazione

### 1. Variabili d'Ambiente

Copia `env.production.example` e configura le variabili:

```bash
cp env.production.example .env.production
```

Modifica `.env.production` con i tuoi valori:

```bash
# Database (Koyeb fornirà questa URL)
DATABASE_URL=postgresql://postgres:password@koyeb-db-host:5432/agriturismo_prod

# JWT (Genera una chiave sicura)
SECRET_KEY=your-super-secret-key-change-this-in-production

# CORS (URL del tuo frontend Netlify)
CORS_ORIGINS=https://your-app.netlify.app,https://your-domain.is-a.dev

# Email (opzionale)
SENDGRID_API_KEY=your-sendgrid-api-key
```

### 2. Genera Chiave Segreta

```bash
# Genera una chiave segreta sicura
python -c "import secrets; print(secrets.token_hex(32))"
```

## 🚀 Deploy Automatico

### Opzione 1: Script Automatico

```bash
# Rendi eseguibile lo script
chmod +x deploy-koyeb.sh

# Imposta le variabili d'ambiente
export DATABASE_URL="your-database-url"
export SECRET_KEY="your-secret-key"
export CORS_ORIGINS="https://your-frontend.netlify.app"

# Esegui il deploy
./deploy-koyeb.sh
```

### Opzione 2: Deploy Manuale

#### Passo 1: Login Koyeb

```bash
# Installa Koyeb CLI
curl -fsSL https://cli.koyeb.com/install.sh | bash

# Login
koyeb auth login
```

#### Passo 2: Crea Database PostgreSQL

```bash
# Crea database su Koyeb
koyeb database create agriturismo-db \
    --type postgresql \
    --version 14 \
    --region fra

# Ottieni URL del database
koyeb database get agriturismo-db --output json | jq -r '.database.url'
```

#### Passo 3: Deploy Applicazione

```bash
# Build Docker image
docker build -t agriturismo-backend .

# Deploy su Koyeb
koyeb app init agriturismo-backend \
    --docker agriturismo-backend:latest \
    --ports 8000:http \
    --routes /:8000 \
    --env DATABASE_URL="your-database-url" \
    --env SECRET_KEY="your-secret-key" \
    --env CORS_ORIGINS="https://your-frontend.netlify.app" \
    --env ENABLE_SSL_REDIRECT="True"
```

## 🔗 Integrazione con Frontend

### Aggiorna Frontend

Nel tuo frontend Angular, aggiorna l'URL dell'API:

```typescript
// environment.prod.ts
export const environment = {
  production: true,
  apiUrl: 'https://your-app-name.koyeb.app',
  // altre configurazioni...
};
```

### Configura CORS

Assicurati che `CORS_ORIGINS` includa l'URL del tuo frontend:

```bash
CORS_ORIGINS=https://your-app.netlify.app,https://your-domain.is-a.dev
```

## 📊 Monitoraggio

### Health Check

```bash
# Verifica che l'app sia online
curl https://your-app-name.koyeb.app/health
```

### Logs

```bash
# Visualizza logs in tempo reale
koyeb app logs agriturismo-backend --follow
```

### Metrics

```bash
# Visualizza metriche dell'app
koyeb app get agriturismo-backend --output json
```

## 🔄 Aggiornamenti

Per aggiornare l'applicazione:

```bash
# Build nuova immagine
docker build -t agriturismo-backend .

# Deploy aggiornamento
koyeb app update agriturismo-backend \
    --docker agriturismo-backend:latest
```

## 🛠️ Troubleshooting

### Problemi Comuni

1. **Database Connection Error**
   ```bash
   # Verifica URL database
   koyeb database get agriturismo-db --output json
   ```

2. **Build Error**
   ```bash
   # Verifica Dockerfile
   docker build -t test-build .
   ```

3. **CORS Error**
   - Verifica `CORS_ORIGINS` nel frontend
   - Controlla che l'URL sia esatto

### Logs di Debug

```bash
# Logs dettagliati
koyeb app logs agriturismo-backend --level debug

# Logs degli ultimi 100 eventi
koyeb app logs agriturismo-backend --limit 100
```

## 💰 Costi

**Koyeb Tier Gratuito include:**
- 0.1 vCPU, 256MB RAM
- PostgreSQL database incluso
- Nessun sleep automatico
- Cold start ~150ms
- 2 applicazioni attive

## 🔐 Sicurezza

### Best Practices

1. **Chiavi Segrete**: Usa sempre chiavi sicure per `SECRET_KEY`
2. **CORS**: Limita `CORS_ORIGINS` solo ai domini necessari
3. **Database**: Non esporre mai le credenziali del database
4. **HTTPS**: Koyeb fornisce SSL automatico

### Variabili Sensibili

```bash
# Non committare mai questi file
.env.production
.env.local
```

## 📞 Supporto

- **Koyeb Docs**: [docs.koyeb.com](https://docs.koyeb.com)
- **Koyeb Community**: [community.koyeb.com](https://community.koyeb.com)
- **GitHub Issues**: Per problemi specifici del progetto

---

🎉 **Congratulazioni!** Il tuo backend è ora deployato su Koyeb e pronto per la produzione! 