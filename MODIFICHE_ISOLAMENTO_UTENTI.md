# Modifiche Backend - Isolamento Dati Utenti

## Data: 9 Ottobre 2025

## 🎯 Obiettivo
Implementare l'isolamento completo dei dati tra utenti diversi nel backend, garantendo che ogni utente veda e possa modificare **esclusivamente i propri dati**.

---

## 🔒 Cosa è Cambiato

### Problema Risolto
Prima delle modifiche, anche se il sistema supportava utenti multipli, gli endpoint API **non filtravano correttamente** i dati in base all'utente loggato. Questo causava:
- ✗ Utenti diversi vedevano gli stessi appartamenti
- ✗ Utenti diversi vedevano gli stessi inquilini
- ✗ Possibile accesso a dati di altri utenti

### Soluzione Implementata
Tutti gli endpoint che gestiscono risorse (GET, POST, PUT, DELETE) ora:
- ✓ **Richiedono obbligatoriamente l'autenticazione** tramite token JWT
- ✓ **Filtrano automaticamente** i dati in base all'ID dell'utente dal token
- ✓ **Non accettano più** il parametro opzionale `user_id` nelle query

---

## 📋 Endpoint Modificati

### 1. **Appartamenti** (`/apartments`)
| Endpoint | Metodo | Modifiche |
|----------|--------|-----------|
| `/apartments/` | GET | Ora richiede autenticazione e filtra per `current_user.id` |
| `/apartments/{id}` | GET | Verifica che l'appartamento appartenga all'utente |
| `/apartments/` | POST | Associa automaticamente il nuovo appartamento all'utente loggato |
| `/apartments/with-images` | POST | Associa automaticamente l'appartamento all'utente loggato |
| `/apartments/{id}` | PUT | Verifica proprietà prima di aggiornare |
| `/apartments/{id}/with-images` | PUT | Verifica proprietà prima di aggiornare |
| `/apartments/{id}` | DELETE | Verifica proprietà prima di eliminare |

### 2. **Inquilini** (`/tenants`)
| Endpoint | Metodo | Modifiche |
|----------|--------|-----------|
| `/tenants/` | GET | Ora richiede autenticazione e filtra per `current_user.id` |
| `/tenants/{id}` | GET | Verifica che l'inquilino appartenga all'utente |
| `/tenants/` | POST | Associa automaticamente il nuovo inquilino all'utente loggato |
| `/tenants/with-images` | POST | Associa automaticamente l'inquilino all'utente loggato |
| `/tenants/{id}` | PUT | Verifica proprietà prima di aggiornare |
| `/tenants/{id}/with-images` | PUT | Verifica proprietà prima di aggiornare |
| `/tenants/{id}` | DELETE | Verifica proprietà prima di eliminare |
| `/tenants/{id}/communication-preferences` | PATCH | Verifica proprietà prima di aggiornare |

### 3. **Utenze** (`/utilities`)
| Endpoint | Metodo | Modifiche |
|----------|--------|-----------|
| `/utilities/` | GET | Ora richiede autenticazione e filtra per `current_user.id` |
| `/utilities/` | POST | Verifica che l'appartamento appartenga all'utente |
| `/utilities/{id}` | PUT | Verifica proprietà prima di aggiornare |
| `/utilities/{id}` | DELETE | Verifica proprietà prima di eliminare |

### 4. **Fatture** (`/invoices`)
| Endpoint | Metodo | Modifiche |
|----------|--------|-----------|
| `/invoices/` | GET | Ora richiede autenticazione e filtra per `current_user.id` |
| `/invoices/` | POST | Associa automaticamente la fattura all'utente loggato |
| `/invoices/{id}` | DELETE | Verifica proprietà prima di eliminare |

### 5. **Contratti di Locazione** (`/leases`)
| Endpoint | Metodo | Modifiche |
|----------|--------|-----------|
| `/leases/` | GET | Ora richiede autenticazione e filtra per `current_user.id` |
| `/leases/{id}` | GET | Verifica che il contratto appartenga all'utente |
| `/leases/` | POST | Associa automaticamente il contratto all'utente loggato |

---

## 📱 Impatto sull'App Flutter

### ✅ Modifiche NON Necessarie (nella maggior parte dei casi)

Se l'app Flutter **sta già inviando il token JWT** nell'header `Authorization`, **non sono necessarie modifiche al codice**. L'app continuerà a funzionare normalmente.

#### Verifica che l'app stia facendo questo:
```dart
// Esempio di chiamata HTTP corretta
final response = await http.get(
  Uri.parse('$baseUrl/apartments/'),
  headers: {
    'Authorization': 'Bearer $token', // ✓ Token JWT nell'header
    'Content-Type': 'application/json',
  },
);
```

### ⚠️ Modifiche Necessarie (se presenti)

#### 1. **Rimuovere il parametro `user_id` dalle chiamate API**

**PRIMA** (non più necessario):
```dart
// ✗ Non serve più passare user_id
final response = await http.get(
  Uri.parse('$baseUrl/apartments/?user_id=$userId'),
  headers: {'Authorization': 'Bearer $token'},
);
```

**DOPO** (semplificato):
```dart
// ✓ Il backend estrae user_id dal token automaticamente
final response = await http.get(
  Uri.parse('$baseUrl/apartments/'),
  headers: {'Authorization': 'Bearer $token'},
);
```

#### 2. **Rimuovere `user_id` dal body delle richieste POST**

**PRIMA** (non più necessario):
```dart
// ✗ Non serve più includere userId nel body
final body = {
  'name': 'Appartamento 1',
  'userId': userId,  // ← Rimuovi questo
  // ...altri campi
};
```

**DOPO** (semplificato):
```dart
// ✓ Il backend assegna automaticamente l'utente
final body = {
  'name': 'Appartamento 1',
  // ...altri campi
};
```

---

## 🔐 Sicurezza Migliorata

### Prima
- Parametro `user_id` opzionale nelle query
- Il frontend doveva gestire manualmente l'ID utente
- Possibilità di passare ID di altri utenti (vulnerabilità)

### Dopo
- Autenticazione obbligatoria con token JWT
- L'ID utente viene estratto dal token (non modificabile)
- Isolamento completo tra utenti
- Nessuna possibilità di accedere a dati di altri utenti

---

## 🧪 Come Testare

1. **Crea due account diversi** nell'app
2. **Accedi con il primo account** e crea alcuni dati (appartamenti, inquilini, ecc.)
3. **Esci e accedi con il secondo account**
4. **Verifica che non vedi i dati del primo account**
5. **Crea dati con il secondo account**
6. **Torna al primo account** e verifica che vedi solo i tuoi dati

---

## 🚨 Possibili Errori

### Errore 401 Unauthorized
**Causa**: Il token JWT non viene inviato o è scaduto  
**Soluzione**: Verifica che l'app includa l'header `Authorization: Bearer <token>` in tutte le richieste

### Errore 404 Not Found
**Causa**: L'utente sta cercando di accedere a una risorsa che non gli appartiene  
**Soluzione**: Questo è il comportamento corretto - l'utente non può vedere dati di altri utenti

### Errore 500 Internal Server Error con "userId: None"
**Causa**: L'endpoint non è stato aggiornato correttamente  
**Soluzione**: Già risolto in questa implementazione

---

## 📝 Note per gli Sviluppatori Flutter

### Gestione del Token
Assicurati che l'app:
1. **Salvi il token** dopo il login (es. con `shared_preferences` o `flutter_secure_storage`)
2. **Includa il token** in ogni richiesta HTTP agli endpoint protetti
3. **Gestisca il refresh** del token quando scade
4. **Reindirizza al login** quando riceve un errore 401

### Esempio di Servizio HTTP
```dart
class ApiService {
  static const baseUrl = 'https://your-api.com';
  
  Future<String?> _getToken() async {
    // Recupera il token salvato
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('auth_token');
  }
  
  Future<http.Response> get(String endpoint) async {
    final token = await _getToken();
    return await http.get(
      Uri.parse('$baseUrl$endpoint'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
    );
  }
  
  Future<http.Response> post(String endpoint, Map<String, dynamic> body) async {
    final token = await _getToken();
    return await http.post(
      Uri.parse('$baseUrl$endpoint'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(body),
    );
  }
}
```

---

## ✅ Checklist Implementazione Flutter

- [ ] Verificare che tutte le chiamate API includano l'header `Authorization`
- [ ] Rimuovere il parametro `user_id` dalle query string
- [ ] Rimuovere il campo `userId` dai body delle richieste POST
- [ ] Testare il login con utenti diversi
- [ ] Verificare l'isolamento dei dati
- [ ] Gestire correttamente gli errori 401 (token scaduto)
- [ ] Implementare il refresh automatico del token

---

## 📞 Supporto

In caso di problemi dopo le modifiche:
1. Verifica i log del backend per errori specifici
2. Controlla che il token JWT sia valido e non scaduto
3. Assicurati che l'app invii correttamente l'header Authorization
4. Testa con strumenti come Postman per isolare il problema

---

**Versione Backend**: Aggiornato il 9 Ottobre 2025  
**Compatibilità**: Richiede client che gestiscano correttamente l'autenticazione JWT
