# 🚀 Deploy Manuale su Koyeb

## Passo 1: Preparazione GitHub

1. **Push del codice su GitHub**
   ```bash
   git add .
   git commit -m "Preparazione deploy Koyeb"
   git push origin main
   ```

2. **Genera chiave segreta**
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

## Passo 2: Setup Koyeb

1. **Registrati su [koyeb.com](https://koyeb.com)**
2. **Connetti il tuo account GitHub**
3. **Crea un nuovo progetto**

## Passo 3: Crea Database PostgreSQL

1. **Dashboard Koyeb → Databases**
2. **"Create Database"**
3. **Configurazione:**
   - Name: `agriturismo-db`
   - Type: `PostgreSQL`
   - Version: `14`
   - Region: `Frankfurt (fra)`
4. **Copia l'URL del database**

## Passo 4: Deploy Applicazione

1. **Dashboard Koyeb → Apps**
2. **"Create App"**
3. **Source:**
   - Git provider: `GitHub`
   - Repository: `your-username/Agriturismo_Backend`
   - Branch: `main`
4. **Build & Deploy:**
   - Builder: `Dockerfile`
   - Port: `8000`
5. **Environment Variables:**
   ```
   DATABASE_URL=postgresql://postgres:password@host:5432/dbname
   SECRET_KEY=your-generated-secret-key
   CORS_ORIGINS=https://your-frontend.netlify.app
   ENABLE_SSL_REDIRECT=True
   ```

## Passo 5: Verifica Deploy

1. **Aspetta il completamento del build**
2. **Testa l'endpoint:**
   ```bash
   curl https://your-app-name.koyeb.app/health
   ```
3. **Verifica logs:**
   - Dashboard → App → Logs

## Passo 6: Aggiorna Frontend

Nel tuo frontend Angular, aggiorna `environment.prod.ts`:
```typescript
export const environment = {
  production: true,
  apiUrl: 'https://your-app-name.koyeb.app',
  // altre configurazioni...
};
```

## ✅ Completato!

Il tuo backend è ora live su Koyeb! 🎉

**URL Backend:** `https://your-app-name.koyeb.app`
**Database:** PostgreSQL incluso nel tier gratuito
**SSL:** Automatico
**Uptime:** 99.9% 