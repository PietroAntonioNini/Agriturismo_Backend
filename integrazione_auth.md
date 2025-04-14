# Guida all'Integrazione dell'Autenticazione

Questo documento fornisce dettagli sull'implementazione dell'autenticazione nel backend FastAPI e come integrare queste funzionalità con il frontend Angular.

## 1. Implementazione Backend

### 1.1 Panoramica

Il backend implementa un sistema di autenticazione completo utilizzando:
- JWT (JSON Web Token) per la gestione delle sessioni
- Hashing delle password con bcrypt
- OAuth2 per la sicurezza delle API

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

### 1.3 Endpoints API

#### 1.3.1 Autenticazione

| Metodo | Endpoint | Descrizione | Payload | Risposta |
|--------|----------|-------------|---------|----------|
| POST | `/api/auth/login` | Ottiene token JWT | `username`, `password` | `accessToken`, `tokenType` |
| POST | `/api/auth/register` | Registra nuovo utente | `UserCreate` | `User` |
| POST | `/api/auth/refresh-token` | Rinnova token JWT | - | `accessToken`, `tokenType` |
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

#### Token Response
```json
{
  "accessToken": "string",
  "tokenType": "bearer"
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
- `exp`: Data di scadenza (30 minuti dalla generazione)
- `iat`: Data di generazione del token

## 2. Guida all'Integrazione con Frontend Angular

### 2.1 Configurazione richiesta

Per integrare l'autenticazione con Angular:

1. Installa la libreria JWT per Angular:
```bash
npm install @auth0/angular-jwt
```

2. Configura un modulo per l'autenticazione che:
   - Gestisca la memorizzazione dei token JWT
   - Aggiunga automaticamente il token a tutte le richieste API
   - Intercetti le risposte 401 per il refresh automatico del token

3. Crea componenti per:
   - Login
   - Registrazione
   - Cambio password
   - Protezione delle rotte private

### 2.2 Interazione con gli endpoint

#### Login
```typescript
// Formato per il login
const credentials = {
  username: 'username',
  password: 'password'
};

// Richiesta di login
this.http.post<TokenResponse>('/api/auth/login', credentials)
  .subscribe(response => {
    localStorage.setItem('access_token', response.accessToken);
    // Reindirizzamento o altra logica
  });
```

#### Refresh Token
```typescript
// Richiesta di refresh token
this.http.post<TokenResponse>('/api/auth/refresh-token', {})
  .subscribe(response => {
    localStorage.setItem('access_token', response.accessToken);
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

## 3. Best Practices e Considerazioni sulla Sicurezza

1. **Memorizzazione sicura**:
   - Salvare solo il token JWT in localStorage o sessionStorage
   - Non memorizzare mai password o dati sensibili

2. **Refresh token**:
   - Implementare un meccanismo di refresh automatico quando il token sta per scadere
   - Logout automatico quando il refresh fallisce

3. **HTTPS**:
   - Utilizzare HTTPS in produzione per proteggere i dati in transito
   - Configurare correttamente i cookie con flag Secure e HttpOnly

4. **CORS**:
   - Limitare gli origin alle sole applicazioni client autorizzate
   - Il backend è già configurato per accettare richieste dal frontend Angular

5. **XSS e CSRF**:
   - Sanitizzare tutti gli input utente
   - Utilizzare httpOnly cookies quando possibile

6. **Rate Limiting**:
   - Il backend implementa limiti di richieste per prevenire attacchi di forza bruta
   - Aggiungere ritardi progressivi dopo tentativi di login falliti

---
