# Guida all'Integrazione dell'Autenticazione e Sicurezza

Questo documento fornisce dettagli sull'implementazione dell'autenticazione e sicurezza nel backend FastAPI e come integrare queste funzionalità con il frontend Angular.

## 1. Implementazione Backend

### 1.1 Panoramica

Il backend implementa un sistema di autenticazione e sicurezza completo utilizzando:
- JWT (JSON Web Token) per la gestione delle sessioni
- Refresh Token per l'autenticazione persistente
- Hashing delle password con bcrypt
- OAuth2 per la sicurezza delle API
- Rate limiting per protezione contro attacchi
- Validazione password per garantire sicurezza
- Caching per migliorare le performance
- Security Headers per protezione avanzata
- Protezione CSRF per prevenire attacchi Cross-Site Request Forgery
- Redirect HTTPS per garantire connessioni sicure

### 1.2 Tabella utenti

La tabella `users` contiene i seguenti campi:
```
users
│
├── id (Integer, PK) - Identificativo univoco
├── username (String, unique) - Nome utente
├── email (String, unique) - Email
├── hashedPassword (String) - Password criptata
├── firstName (String) - Nome
├── lastName (String) - Cognome
├── role (String) - Ruolo (admin, manager, staff)
├── isActive (Boolean) - Stato dell'account
├── lastLogin (DateTime) - Data ultimo accesso
├── createdAt (DateTime) - Data creazione
└── updatedAt (DateTime) - Data aggiornamento
```

La tabella `refresh_tokens` contiene:
```
refresh_tokens
│
├── id (Integer, PK) - Identificativo univoco
├── token (String, unique) - Token univoco
├── username (String, FK) - Username dell'utente
├── expires (DateTime) - Data di scadenza
├── created_at (DateTime) - Data creazione
├── is_revoked (Boolean) - Se il token è stato revocato
└── revoked_at (DateTime) - Data di revoca
```

### 1.3 Endpoints API

#### 1.3.1 Autenticazione

| Metodo | Endpoint | Descrizione | Payload | Risposta |
|--------|----------|-------------|---------|----------|
| POST | `/api/auth/login` | Ottiene token di accesso e refresh | `username`, `password` | `accessToken`, `refreshToken`, `tokenType`, `expiresIn` |
| POST | `/api/auth/register` | Registra nuovo utente | `UserCreate` | `User` |
| POST | `/api/auth/refresh-token` | Rinnova i token | `refresh_token` | `accessToken`, `refreshToken`, `tokenType`, `expiresIn` |
| POST | `/api/auth/logout` | Revoca token | `refresh_token` | Messaggio di successo |
| POST | `/api/auth/logout-all` | Revoca tutti i token | - | Messaggio di successo |
| GET | `/api/auth/verify-token` | Verifica validità token | - | Informazioni utente |
| PUT | `/api/auth/change-password` | Cambia password | `currentPassword`, `newPassword` | Messaggio di successo |
| GET | `/api/auth/csrf-token` | Ottiene token CSRF | - | `csrf_token`, `expires` |

#### 1.3.2 Utenti

| Metodo | Endpoint | Descrizione | Risposta |
|--------|----------|-------------|----------|
| GET | `/api/users/me` | Info utente corrente | `User` |
| GET | `/api/users/` | Lista utenti (solo admin) | `List[User]` |

### 1.4 Schema Dati e Payload

#### UserCreate
```json
{
  "username": "string",
  "email": "user@example.com",
  "firstName": "string",
  "lastName": "string",
  "role": "string",
  "isActive": true,
  "password": "string"
}
```

#### User Response
```json
{
  "username": "string",
  "email": "user@example.com",
  "firstName": "string",
  "lastName": "string",
  "role": "string",
  "isActive": true,
  "id": 0,
  "lastLogin": "2023-01-01T00:00:00.000Z",
  "createdAt": "2023-01-01T00:00:00.000Z",
  "updatedAt": "2023-01-01T00:00:00.000Z"
}
```

#### TokenPair Response
```json
{
  "accessToken": "string",
  "refreshToken": "string",
  "tokenType": "bearer",
  "expiresIn": 3600
}
```

#### UserPasswordChange
```json
{
  "currentPassword": "string",
  "newPassword": "string"
}
```

#### CSRF Token Response
```json
{
  "csrf_token": "string",
  "expires": "2023-01-01T00:00:00.000Z"
}
```

### 1.5 Formato e Sicurezza JWT

I token JWT contengono le seguenti informazioni (payload):
```json
{
  "sub": "username",
  "role": "admin/manager/staff",
  "exp": 1609459200,
  "iat": 1609455600
}
```

Dove:
- `sub`: Username dell'utente
- `role`: Ruolo dell'utente
- `exp`: Data di scadenza (60 minuti dalla generazione)
- `iat`: Data di generazione del token

### 1.6 Refresh Token

I refresh token sono stringhe UUID casuali memorizzate nel database per un accesso persistente:
- Durata: 30 giorni (configurabile)
- Sono revocabili singolarmente o completamente per un utente
- Si rinnovano ad ogni utilizzo per maggiore sicurezza
- Vengono revocati automaticamente al cambio password

### 1.7 Rate Limiting

Per proteggere da attacchi di forza bruta, il backend implementa limiti di richieste:
- Login: 5 tentativi al minuto
- Registrazione: 3 tentativi al minuto
- Endpoint generici: 60 richieste al minuto

### 1.8 Validazione Password

Per garantire sicurezza, le password devono rispettare i seguenti requisiti:
- Lunghezza minima: 8 caratteri
- Almeno una lettera maiuscola
- Almeno una lettera minuscola
- Almeno un numero
- Almeno un carattere speciale

### 1.9 Security Headers

Il backend implementa diversi header di sicurezza:
- `Strict-Transport-Security`: Forza l'uso di HTTPS
- `Content-Security-Policy`: Previene attacchi XSS
- `X-Content-Type-Options`: Previene il MIME sniffing
- `X-Frame-Options`: Protegge dal clickjacking
- `X-XSS-Protection`: Protezione XSS aggiuntiva
- `Referrer-Policy`: Limita le informazioni nei header referer
- `Permissions-Policy`: Controlla l'accesso alle API del browser

### 1.10 Protezione CSRF

Il backend implementa protezione CSRF per le operazioni POST/PUT/DELETE:
- Token JWT firmati con una chiave segreta
- Cookie HttpOnly per il token CSRF
- Validazione dei token per le operazioni di modifica

### 1.11 Caching

Le richieste GET vengono memorizzate nella cache per migliorare le performance:
- Durata predefinita: 60 secondi
- Esclusione degli endpoint di autenticazione e dati utente
- Inclusione di header di cache per controllo client-side

## 2. Guida all'Integrazione con Frontend Angular

### 2.1 Configurazione richiesta

Per integrare l'autenticazione e sicurezza con Angular:

1. Installa le librerie necessarie:
```bash
npm install @auth0/angular-jwt
```

2. Configura un modulo per l'autenticazione che:
   - Gestisca la memorizzazione dei token JWT e refresh token
   - Aggiunga automaticamente il token a tutte le richieste API
   - Intercetti le risposte 401 per il refresh automatico del token
   - Implementi logout locale e remoto
   - Gestisca la protezione CSRF

3. Crea componenti per:
   - Login
   - Registrazione
   - Cambio password
   - Protezione delle rotte private
   - Gestione errori di autenticazione

### 2.2 Interazione con gli endpoint di autenticazione

#### Login
```typescript
// Formato per il login
const credentials = {
  username: 'username',
  password: 'password'
};

// Richiesta di login
this.http.post<TokenPair>('/api/auth/login', credentials)
  .subscribe(response => {
    // Salva entrambi i token
    localStorage.setItem('access_token', response.accessToken);
    localStorage.setItem('refresh_token', response.refreshToken);
    localStorage.setItem('expires_at', new Date().getTime() + response.expiresIn * 1000);
    // Reindirizzamento o altra logica
  });
```

#### Refresh Token
```typescript
// Richiesta di refresh token (quando l'access token sta per scadere)
const refreshToken = localStorage.getItem('refresh_token');
this.http.post<TokenPair>('/api/auth/refresh-token', { refresh_token: refreshToken })
  .subscribe(response => {
    localStorage.setItem('access_token', response.accessToken);
    localStorage.setItem('refresh_token', response.refreshToken);
    localStorage.setItem('expires_at', new Date().getTime() + response.expiresIn * 1000);
  });
```

#### Logout
```typescript
// Richiesta di logout (singolo dispositivo)
const refreshToken = localStorage.getItem('refresh_token');
this.http.post('/api/auth/logout', { refresh_token: refreshToken })
  .subscribe(response => {
    // Rimuovi token memorizzati localmente
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('expires_at');
    localStorage.removeItem('csrf_token'); // Rimuovi anche il token CSRF
    // Reindirizzamento al login
  });

// Logout da tutti i dispositivi
this.http.post('/api/auth/logout-all', {})
  .subscribe(response => {
    // Rimuovi token memorizzati localmente
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('expires_at');
    localStorage.removeItem('csrf_token'); // Rimuovi anche il token CSRF
    // Reindirizzamento al login
  });
```

#### Cambio Password
```typescript
// Formato per il cambio password
const passwordData = {
  currentPassword: 'current-password',
  newPassword: 'new-password'
};

// Richiesta di cambio password (con token CSRF)
this.http.put('/api/auth/change-password', passwordData, {
  headers: { 'X-CSRF-Token': localStorage.getItem('csrf_token') }
})
  .subscribe(response => {
    // Gestione risposta
  });
```

#### Verifica validità token
```typescript
// Verifica se il token è valido e ottieni informazioni utente
this.http.get('/api/auth/verify-token')
  .subscribe(user => {
    // Il token è valido, salva le informazioni utente
    this.currentUser = user;
  }, error => {
    // Token non valido, reindirizza al login
    this.router.navigate(['/login']);
  });
```

### 2.3 Implementazione protezione CSRF

#### Ottenere un token CSRF
```typescript
// Richiesta per ottenere il token CSRF
this.http.get<{csrf_token: string, expires: string}>('/api/auth/csrf-token')
  .subscribe(response => {
    // Salva il token CSRF (il cookie viene impostato automaticamente dal backend)
    localStorage.setItem('csrf_token', response.csrf_token);
  });
```

#### Aggiungere il token CSRF alle richieste POST/PUT/DELETE
```typescript
// Esempio di invio dati con protezione CSRF
const data = { /* i dati da inviare */ };
this.http.post('/api/endpoint', data, {
  headers: { 'X-CSRF-Token': localStorage.getItem('csrf_token') }
})
  .subscribe(response => {
    // Gestione risposta
  });
```

### 2.4 Protezione delle rotte

Utilizzare il guard di Angular per proteggere le rotte:

```typescript
// auth.guard.ts
@Injectable({
  providedIn: 'root'
})
export class AuthGuard implements CanActivate {
  
  constructor(private authService: AuthService, private router: Router) {}
  
  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): boolean {
    if (!this.authService.isAuthenticated()) {
      this.router.navigate(['/login']);
      return false;
    }
    
    // Controllo ruoli se necessario
    const requiredRole = route.data.role;
    if (requiredRole && !this.authService.hasRole(requiredRole)) {
      this.router.navigate(['/unauthorized']);
      return false;
    }
    
    return true;
  }
}
```

### 2.5 Interceptor HTTP con gestione CSRF e JWT

Implementare un interceptor HTTP che gestisca automaticamente i token JWT e CSRF:

```typescript
// auth.interceptor.ts
@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  private isRefreshing = false;
  private refreshTokenSubject: BehaviorSubject<any> = new BehaviorSubject<any>(null);

  constructor(private authService: AuthService) {}

  intercept(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    // Aggiungi JWT token a tutte le richieste (tranne login e refresh)
    if (!request.url.includes('/auth/login') && !request.url.includes('/auth/refresh-token')) {
      request = this.addAuthToken(request);
    }

    // Aggiungi CSRF token a tutte le richieste di modifica (POST/PUT/DELETE/PATCH)
    if (this.requiresCsrfToken(request.method)) {
      request = this.addCsrfToken(request);
    }

    return next.handle(request).pipe(
      catchError(error => {
        if (error instanceof HttpErrorResponse) {
          if (error.status === 401) {
            // Gestione errore 401 (Unauthorized)
            return this.handle401Error(request, next);
          } else if (error.status === 403 && error.error?.detail?.includes('CSRF')) {
            // Gestione errore CSRF
            return this.handleCsrfError(request, next);
          }
        }
        return throwError(error);
      })
    );
  }

  private addAuthToken(request: HttpRequest<any>): HttpRequest<any> {
    const token = localStorage.getItem('access_token');
    
    if (token) {
      // Controlla se il token è vicino alla scadenza
      const expiresAt = Number(localStorage.getItem('expires_at'));
      const isExpiringSoon = expiresAt - 60000 < new Date().getTime(); // 1 minuto prima della scadenza
      
      if (isExpiringSoon && !this.isRefreshing) {
        // Avvia refresh in background
        this.refreshToken();
      }
      
      return request.clone({
        setHeaders: { Authorization: `Bearer ${token}` }
      });
    }
    return request;
  }

  private addCsrfToken(request: HttpRequest<any>): HttpRequest<any> {
    const csrfToken = localStorage.getItem('csrf_token');
    
    if (csrfToken) {
      return request.clone({
        setHeaders: { 'X-CSRF-Token': csrfToken }
      });
    }
    return request;
  }

  private requiresCsrfToken(method: string): boolean {
    return ['POST', 'PUT', 'DELETE', 'PATCH'].includes(method);
  }

  private handleCsrfError(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    // Richiedi un nuovo token CSRF e riprova la richiesta
    return this.authService.getCsrfToken().pipe(
      switchMap(token => {
        localStorage.setItem('csrf_token', token.csrf_token);
        return next.handle(this.addCsrfToken(request));
      })
    );
  }

  private handle401Error(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    if (!this.isRefreshing) {
      this.isRefreshing = true;
      this.refreshTokenSubject.next(null);

      return this.authService.refreshToken().pipe(
        switchMap(token => {
          this.isRefreshing = false;
          this.refreshTokenSubject.next(token.accessToken);
          return next.handle(this.addAuthToken(request));
        }),
        catchError(error => {
          this.isRefreshing = false;
          this.authService.logout();
          return throwError(error);
        })
      );
    } else {
      return this.refreshTokenSubject.pipe(
        filter(token => token != null),
        take(1),
        switchMap(jwt => next.handle(this.addAuthToken(request)))
      );
    }
  }
  
  private refreshToken() {
    this.authService.refreshToken().subscribe();
  }
}
```

### 2.6 Servizio di autenticazione completo

Implementare un servizio di autenticazione che gestisca JWT, Refresh Token e CSRF:

```typescript
// auth.service.ts
@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private currentUserSubject = new BehaviorSubject<any>(null);
  public currentUser = this.currentUserSubject.asObservable();
  
  constructor(private http: HttpClient, private router: Router) {
    // Verifica il token all'avvio dell'applicazione
    this.checkToken();
    // Richiedi un token CSRF all'avvio
    this.getCsrfToken().subscribe();
  }
  
  login(username: string, password: string): Observable<any> {
    return this.http.post<TokenPair>('/api/auth/login', { username, password })
      .pipe(
        map(response => {
          // Salva token
          this.storeTokens(response);
          // Carica i dati utente
          this.loadUserProfile();
          // Richiedi un nuovo token CSRF dopo il login
          this.getCsrfToken().subscribe();
          return response;
        })
      );
  }
  
  register(user: any): Observable<any> {
    return this.http.post('/api/auth/register', user);
  }
  
  getCsrfToken(): Observable<{csrf_token: string, expires: string}> {
    return this.http.get<{csrf_token: string, expires: string}>('/api/auth/csrf-token')
      .pipe(
        tap(response => {
          localStorage.setItem('csrf_token', response.csrf_token);
        })
      );
  }
  
  refreshToken(): Observable<TokenPair> {
    const refreshToken = localStorage.getItem('refresh_token');
    
    if (!refreshToken) {
      this.logout();
      return throwError('No refresh token available');
    }
    
    return this.http.post<TokenPair>('/api/auth/refresh-token', { refresh_token: refreshToken })
      .pipe(
        map(response => {
          this.storeTokens(response);
          return response;
        }),
        catchError(error => {
          this.logout();
          return throwError(error);
        })
      );
  }
  
  logout(): void {
    const refreshToken = localStorage.getItem('refresh_token');
    
    if (refreshToken) {
      // Tenta di revocare il token sul server (anche se fallisce procediamo con il logout locale)
      this.http.post('/api/auth/logout', { refresh_token: refreshToken })
        .subscribe(
          _ => this.clearLocalStorage(),
          _ => this.clearLocalStorage()
        );
    } else {
      this.clearLocalStorage();
    }
  }
  
  logoutAllDevices(): Observable<any> {
    return this.http.post('/api/auth/logout-all', {})
      .pipe(
        finalize(() => this.clearLocalStorage())
      );
  }
  
  changePassword(currentPassword: string, newPassword: string): Observable<any> {
    return this.http.put('/api/auth/change-password', {
      currentPassword,
      newPassword
    });
  }
  
  isAuthenticated(): boolean {
    const token = localStorage.getItem('access_token');
    const expiresAt = Number(localStorage.getItem('expires_at'));
    
    if (!token || !expiresAt) {
      return false;
    }
    
    return new Date().getTime() < expiresAt;
  }
  
  hasRole(role: string): boolean {
    const user = this.currentUserSubject.value;
    return user && user.role === role;
  }
  
  private storeTokens(response: TokenPair): void {
    localStorage.setItem('access_token', response.accessToken);
    localStorage.setItem('refresh_token', response.refreshToken);
    localStorage.setItem('expires_at', String(new Date().getTime() + response.expiresIn * 1000));
  }
  
  private loadUserProfile(): void {
    this.http.get('/api/auth/verify-token')
      .subscribe(
        user => this.currentUserSubject.next(user),
        error => {
          console.error('Failed to load user profile', error);
          // Se non riusciamo a caricare il profilo, il token potrebbe essere invalido
          this.refreshToken().subscribe();
        }
      );
  }
  
  private clearLocalStorage(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('expires_at');
    localStorage.removeItem('csrf_token');
    this.currentUserSubject.next(null);
    this.router.navigate(['/login']);
  }
  
  private checkToken(): void {
    if (this.isAuthenticated()) {
      this.loadUserProfile();
    }
  }
}
```

### 2.7 Configurazione modulo app per il sistema di autenticazione

```typescript
// app.module.ts
@NgModule({
  declarations: [
    AppComponent,
    // ... altri componenti
  ],
  imports: [
    BrowserModule,
    HttpClientModule,
    // ... altri moduli
  ],
  providers: [
    // Configurazione interceptor per gestire JWT e CSRF
    {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true
    },
    // Altri provider
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
```

## 3. Best Practices e Considerazioni sulla Sicurezza

### 3.1 Gestione sicura dei token

- **Access Token JWT**:
  - Memorizzare in localStorage/sessionStorage (compromesso tra sicurezza e usabilità)
  - Impostare una durata breve (30-60 minuti)
  - Non memorizzare dati sensibili nel payload

- **Refresh Token**:
  - Memorizzare in localStorage o preferibilmente in cookie HttpOnly
  - Verificare sempre lato server che non sia stato revocato
  - Usare una durata più lunga (es. 30 giorni) per comodità dell'utente

- **CSRF Token**:
  - Il cookie è gestito automaticamente dal browser (HttpOnly)
  - Memorizzare il valore del token in localStorage/sessionStorage
  - Rinnovare periodicamente o dopo operazioni sensibili

### 3.2 HTTPS e Secure Cookies

- Utilizzare HTTPS in tutti gli ambienti (anche sviluppo)
- Impostare flag `Secure` e `HttpOnly` sui cookie
- Implementare HSTS (Strict-Transport-Security) per evitare attacchi downgrade

### 3.3 Gestione degli errori

- Gestire errori di autorizzazione (401) con refresh automatico
- Gestire errori CSRF (403) con richiesta di nuovo token
- Gestire errori di Rate Limit (429) con backoff esponenziale
- Mostrare messaggi di errore user-friendly senza esporre dettagli tecnici

### 3.4 Gestione del Rate Limiting

```typescript
// Esempio di gestione del rate limiting con backoff esponenziale
@Injectable()
export class RateLimitingInterceptor implements HttpInterceptor {
  private retryDelay = 1000; // 1 secondo
  private maxRetries = 3;
  
  intercept(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    return next.handle(request).pipe(
      retryWhen(errors => errors.pipe(
        concatMap((error, count) => {
          // Gestisce solo errori 429 (Too Many Requests)
          if (error.status !== 429 || count >= this.maxRetries) {
            return throwError(error);
          }
          
          // Calcola il backoff esponenziale
          const delay = this.retryDelay * Math.pow(2, count);
          console.log(`Rate limited. Retrying in ${delay}ms`);
          
          // Mostra un messaggio all'utente
          this.notificationService.warn('Troppe richieste, riprova tra poco');
          
          // Ritarda la richiesta successiva
          return timer(delay);
        })
      ))
    );
  }
}
```

### 3.5 Validazione e Sanitizzazione Input

```typescript
// Esempio di validazione password lato frontend
export function passwordValidator(): ValidatorFn {
  return (control: AbstractControl): {[key: string]: any} | null => {
    const value = control.value;
    
    if (!value) {
      return null;
    }
    
    const hasUpperCase = /[A-Z]/.test(value);
    const hasLowerCase = /[a-z]/.test(value);
    const hasNumeric = /[0-9]/.test(value);
    const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]+/.test(value);
    
    const passwordValid = hasUpperCase && hasLowerCase && hasNumeric && hasSpecial && value.length >= 8;
    
    return !passwordValid ? { invalidPassword: true } : null;
  };
}

// Sanitizzazione input per prevenire XSS
@Pipe({name: 'safeHtml'})
export class SafeHtmlPipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}
  
  transform(value: string): SafeHtml {
    return this.sanitizer.bypassSecurityTrustHtml(value);
  }
}
```

### 3.6 Gestione della Sessione

- Implementare logout automatico dopo inattività
- Offrire opzione "Ricordami" per sessioni più lunghe
- Permettere all'utente di visualizzare e terminare sessioni attive

```typescript
// Esempio di servizio per il monitoraggio dell'inattività
@Injectable({
  providedIn: 'root'
})
export class IdleMonitorService {
  private idle$ = new Subject<boolean>();
  private idleTimeout = 15 * 60 * 1000; // 15 minuti di inattività
  private idleTimer: any;
  
  constructor(private authService: AuthService) {
    // Monitoraggio eventi utente
    fromEvent(document, 'mousemove').pipe(
      throttleTime(1000)
    ).subscribe(() => this.resetIdleTimer());
    
    fromEvent(document, 'keypress').subscribe(() => this.resetIdleTimer());
    
    this.idle$.pipe(
      filter(idle => idle === true)
    ).subscribe(() => {
      // Logout automatico dopo inattività
      this.authService.logout();
      alert('La tua sessione è scaduta per inattività.');
    });
    
    // Inizializza timer
    this.resetIdleTimer();
  }
  
  private resetIdleTimer(): void {
    clearTimeout(this.idleTimer);
    this.idleTimer = setTimeout(() => {
      this.idle$.next(true);
    }, this.idleTimeout);
  }
}
```

## 4. Checklist di integrazione

- [ ] Installazione delle librerie necessarie
- [ ] Implementazione del servizio AuthService
- [ ] Implementazione dell'interceptor per JWT e CSRF
- [ ] Implementazione del guard per le rotte protette
- [ ] Creazione dei componenti di login, registrazione e gestione password
- [ ] Configurazione del modulo app con gli interceptor
- [ ] Test completo del flusso di autenticazione
- [ ] Implementazione della gestione errori e rate limiting
- [ ] Integrazione con il sistema di notifiche dell'applicazione
- [ ] Test di sicurezza (XSS, CSRF, Injection)
</rewritten_file>