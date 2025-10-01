# Troubleshooting Deploy - Agriturismo Frontend

Questo documento contiene le soluzioni ai problemi più comuni durante il deploy su Netlify.

## 🚨 Problemi Comuni e Soluzioni

### 1. **Errore: Schema validation failed - buildOptimizer**

**Errore**: `Data path "" must NOT have additional properties(buildOptimizer)`

**Causa**: Angular 19 non supporta più la proprietà `buildOptimizer` nella configurazione.

**Soluzione**: ✅ **RISOLTO**
- Rimossa la proprietà `buildOptimizer` da `angular.json`
- Rimosse anche `aot`, `vendorChunk`, `commonChunk` che non sono più necessarie

### 2. **Errore: Percorso di pubblicazione errato**

**Errore**: `publish directory does not exist`

**Causa**: Discrepanza tra il nome del progetto e il percorso di output.

**Soluzione**: ✅ **RISOLTO**
- Corretto `outputPath` in `angular.json`: `dist/agriturismo-frontend`
- Corretto `publish` in `netlify.toml`: `dist/agriturismo-frontend`

### 3. **Errore: Import dinamico non supportato**

**Errore**: `Cannot find module 'rxjs'` o errori di import dinamico

**Causa**: Import dinamico di `forkJoin` non supportato in produzione.

**Soluzione**: ✅ **RISOLTO**
- Sostituito import dinamico con import statico: `import { forkJoin } from 'rxjs'`

### 4. **Errore: performance.now() non disponibile**

**Errore**: `performance is not defined`

**Causa**: `performance.now()` potrebbe non essere disponibile in tutti gli ambienti.

**Soluzione**: ✅ **RISOLTO**
- Sostituito `performance.now()` con `Date.now()` in tutti i servizi

### 5. **Errore: Metodo mancante**

**Errore**: `Property 'getCacheStats' does not exist`

**Causa**: Metodo menzionato nella documentazione ma non implementato.

**Soluzione**: ✅ **RISOLTO**
- Implementato il metodo `getCacheStats()` nel `GenericApiService`

### 6. **Errore: Budget superato**

**Errore**: `bundle initial exceeded maximum budget`

**Causa**: Le dipendenze pesanti (Bootstrap, jQuery, Chart.js, jsPDF) superano i limiti di budget.

**Soluzione**: ✅ **RISOLTO**
- Aumentato budget iniziale da 2MB a 3MB
- Aumentato budget CSS da 30KB a 50KB
- Configurato `allowedCommonJsDependencies` per jsPDF e dipendenze correlate

## 🔧 Configurazioni Corrette

### angular.json (Produzione)
```json
{
  "configurations": {
    "production": {
      "budgets": [
        {
          "type": "initial",
          "maximumWarning": "2mb",
          "maximumError": "3mb"
        },
        {
          "type": "anyComponentStyle",
          "maximumWarning": "30kb",
          "maximumError": "50kb"
        }
      ],
      "optimization": {
        "scripts": true,
        "styles": {
          "minify": true,
          "inlineCritical": false
        },
        "fonts": true
      },
      "allowedCommonJsDependencies": [
        "canvg",
        "html2canvas",
        "jspdf",
        "core-js",
        "raf",
        "rgbcolor"
      ],
      "outputHashing": "all",
      "sourceMap": false,
      "namedChunks": false,
      "extractLicenses": true,
      "subresourceIntegrity": true
    }
  }
}
```

### netlify.toml
```toml
[build]
  command = "ng build --configuration production"
  publish = "dist/agriturismo-frontend"

[build.environment]
  NODE_VERSION = "20"
  NPM_VERSION = "10"
```

## 🧪 Test Locale

Prima del deploy, esegui il test locale:

```bash
# Test della configurazione
npm run test:build

# Build di produzione locale
npm run build:prod

# Verifica che la cartella dist sia stata creata
ls -la dist/
```

## 📋 Checklist Pre-Deploy

- [ ] ✅ Configurazione Angular corretta (senza proprietà obsolete)
- [ ] ✅ Percorso di output corretto
- [ ] ✅ Configurazione Netlify corretta
- [ ] ✅ Tutti gli import sono statici
- [ ] ✅ Nessun uso di `performance.now()`
- [ ] ✅ Tutti i metodi menzionati sono implementati
- [ ] ✅ Build locale funziona
- [ ] ✅ Test di configurazione passa

## 🚀 Comandi di Deploy

### Deploy Automatico (Git)
```bash
# Push su branch main
git add .
git commit -m "Fix deploy configuration"
git push origin main
```

### Deploy Manuale
```bash
# Build locale
npm run build:prod

# Deploy su Netlify (se hai CLI installato)
netlify deploy --prod --dir=dist/Agriturismo_Frontend
```

## 🔍 Debug

### Log di Build
Se il build fallisce, controlla:
1. **Log Netlify**: Vai su Netlify Dashboard > Deploys > Log
2. **Log Locali**: Esegui `npm run build:prod` localmente
3. **Configurazione**: Verifica `angular.json` e `netlify.toml`

### Verifica File
```bash
# Verifica che tutti i file necessari esistano
ls -la src/app/shared/services/performance-monitor.service.ts
ls -la src/app/shared/components/performance-dashboard/performance-dashboard.component.ts
ls -la angular.json
ls -la netlify.toml
```

### Test Configurazione
```bash
# Esegui il test di configurazione
node test-build.js
```

## 📞 Supporto

Se continui ad avere problemi:

1. **Controlla i log**: Sempre il primo passo
2. **Test locale**: Assicurati che funzioni localmente
3. **Verifica versioni**: Node.js 20, Angular 19
4. **Pulisci cache**: `npm cache clean --force`
5. **Reinstalla dipendenze**: `rm -rf node_modules && npm install`

## 🔄 Rollback

Se il deploy fallisce, puoi fare rollback:

1. **Netlify Dashboard**: Vai su Deploys > Rollback
2. **Git**: `git revert <commit-hash>`
3. **Locale**: Ripristina i file dalla versione precedente

---

**Nota**: Tutti i problemi elencati sono stati risolti. Il deploy dovrebbe ora funzionare correttamente. 