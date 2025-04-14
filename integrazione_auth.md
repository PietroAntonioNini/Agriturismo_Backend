# Guida all'Integrazione dell'Autenticazione

Questo documento fornisce dettagli sull'implementazione dell'autenticazione nel backend FastAPI e come integrare queste funzionalità con il frontend Angular.

## 1. Implementazione Backend

### 1.1 Panoramica

Il backend implementa un sistema di autenticazione completo utilizzando:
- JWT (JSON Web Token) per la gestione delle sessioni
- Refresh Token per l'autenticazione persistente
- Hashing delle password con bcrypt
- OAuth2 per la sicurezza delle API
- Rate limiting per protezione contro attacchi
- Validazione password per garantire sicurezza
- Caching per migliorare le performance

### 1.2 Tabella utenti

La tabella `users` contiene i seguenti campi:
```
users
│
├── id (Integer, PK) - Identificativo univoco
├── username (String, unique) - Nome utente
├── email (String, unique) - Email
├── hashed_password (String) - Password criptata
├── first_name (String) - Nome
├── last_name (String) - Cognome
├── role (String) - Ruolo (admin, manager, staff)
├── is_active (Boolean) - Stato dell'account
├── last_login (DateTime) - Data ultimo accesso
├── created_at (DateTime) - Data creazione
└── updated_at (DateTime) - Data aggiornamento
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

### 1.9 Caching

Le richieste GET vengono memorizzate nella cache per migliorare le performance:
- Durata predefinita: 60 secondi
- Esclusione degli endpoint di autenticazione
- Inclusione di header di cache per controllo client-side

## 2. Guida all'Integrazione con Frontend Angular

### 2.1 Configurazione richiesta

Per integrare l'autenticazione con Angular:

1. Installa le librerie necessarie:
```bash
npm install @auth0/angular-jwt
```

2. Configura un modulo per l'autenticazione che:
   - Gestisca la memorizzazione dei token JWT e refresh token
   - Aggiunga automaticamente il token a tutte le richieste API
   - Intercetti le risposte 401 per il refresh automatico del token
   - Implementi logout locale e remoto

3. Crea componenti per:
   - Login
   - Registrazione
   - Cambio password
   - Protezione delle rotte private
   - Gestione errori di autenticazione

### 2.2 Interazione con gli endpoint

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
    // Reindirizzamento al login
  });

// Logout da tutti i dispositivi
this.http.post('/api/auth/logout-all', {})
  .subscribe(response => {
    // Rimuovi token memorizzati localmente
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('expires_at');
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

// Richiesta di cambio password
this.http.put('/api/auth/change-password', passwordData)
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

### 2.3 Protezione delle rotte

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

### 2.4 Gestione automatizzata refresh token

Implementare un interceptor che gestisca automaticamente i refresh token:

```typescript
// token.interceptor.ts
@Injectable()
export class TokenInterceptor implements HttpInterceptor {
  private isRefreshing = false;
  private refreshTokenSubject: BehaviorSubject<any> = new BehaviorSubject<any>(null);

  constructor(private authService: AuthService) {}

  intercept(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    // Aggiungi token a tutte le richieste non di autenticazione
    if (!request.url.includes('/auth/login') && !request.url.includes('/auth/refresh-token')) {
      request = this.addToken(request);
    }

    return next.handle(request).pipe(
      catchError(error => {
        if (error instanceof HttpErrorResponse && error.status === 401) {
          return this.handle401Error(request, next);
        }
        return throwError(error);
      })
    );
  }

  private addToken(request: HttpRequest<any>): HttpRequest<any> {
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

  private handle401Error(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    if (!this.isRefreshing) {
      this.isRefreshing = true;
      this.refreshTokenSubject.next(null);

      return this.authService.refreshToken().pipe(
        switchMap(token => {
          this.isRefreshing = false;
          this.refreshTokenSubject.next(token.accessToken);
          return next.handle(this.addToken(request));
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
        switchMap(jwt => next.handle(this.addToken(request)))
      );
    }
  }
  
  private refreshToken() {
    this.authService.refreshToken().subscribe();
  }
}
```

## 3. Best Practices e Considerazioni sulla Sicurezza

1. **Memorizzazione sicura**:
   - Salvare token JWT in localStorage per sessioni brevi o sessionStorage per maggiore sicurezza
   - Considerare l'uso di cookie HttpOnly per il refresh token in produzione

2. **Refresh token**:
   - Implementare sempre un check della scadenza prima di ogni richiesta
   - Gestire i casi di token revocati o non validi con reindirizzamento al login
   - Assicurarsi che il logout revochi sempre il refresh token sul server

3. **HTTPS**:
   - Utilizzare HTTPS in tutti gli ambienti, inclusi test e sviluppo
   - Configurare correttamente i cookie con flag Secure e HttpOnly
   - Impostare header di sicurezza come HSTS

4. **CORS**:
   - Il backend è già configurato per accettare richieste da origini specifiche
   - Mantenere aggiornata la lista delle origini consentite in `settings.cors_origins`
   - Utilizzare credenziali nelle richieste CORS (`withCredentials: true`)

5. **XSS e CSRF**:
   - Sanitizzare tutti gli input utente con l'apposito servizio Angular
   - Evitare l'uso di `innerHTML` o altre API che potrebbero causare vulnerabilità XSS
   - Implementare CSRF token per operazioni critiche

6. **Rate Limiting**:
   - Il backend implementa limiti di richieste per prevenire attacchi di forza bruta
   - Gestire le risposte 429 (Too Many Requests) con exponential backoff
   - Aggiungere indicatori visivi durante i tentativi di login/registrazione

7. **Password Sicure**:
   - Implementare un indicatore di robustezza password in fase di registrazione
   - Fornire suggerimenti all'utente sulle regole per la creazione di password
   - Limitare i tentativi falliti di login con un sistema di blocco temporaneo

8. **Caching**:
   - Utilizzare correttamente gli header di cache nelle richieste Angular
   - Non memorizzare informazioni sensibili nella cache del browser
   - Sfruttare il caching del server per risorse frequentemente utilizzate

## 4. Esempio di Implementazione del Servizio Auth in Angular

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
  }
  
  login(username: string, password: string): Observable<any> {
    return this.http.post<TokenPair>('/api/auth/login', { username, password })
      .pipe(
        map(response => {
          // Salva token
          this.storeTokens(response);
          // Carica i dati utente
          this.loadUserProfile();
          return response;
        })
      );
  }
  
  register(user: any): Observable<any> {
    return this.http.post('/api/auth/register', user);
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
    this.currentUserSubject.next(null);
    this.router.navigate(['/login']);
  }
  
  private checkToken(): void {
    if (this.isAuthenticated()) {
      this.loadUserProfile();
    }
  }
}