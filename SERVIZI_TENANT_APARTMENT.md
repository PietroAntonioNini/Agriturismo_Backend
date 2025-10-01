# Servizi per Tenant e Apartment

## Panoramica

Per completare il sistema di fatturazione, è necessario implementare i servizi per gestire i dati di **Tenant** (Inquilini) e **Apartment** (Appartamenti). Attualmente i componenti utilizzano dati mock, ma per un sistema completo è necessario implementare i servizi reali.

## 1. Servizio Tenant

### 1.1 Interfaccia Tenant
```typescript
// src/app/shared/models/tenant.model.ts
export interface Tenant {
  id: number;
  name: string;
  email: string;
  phone: string;
  address: string;
  fiscalCode: string;
  birthDate: Date;
  emergencyContact?: {
    name: string;
    phone: string;
    relationship: string;
  };
  documents: TenantDocument[];
  createdAt: Date;
  updatedAt: Date;
}

export interface TenantDocument {
  id: number;
  type: 'identity' | 'contract' | 'other';
  name: string;
  url: string;
  uploadedAt: Date;
}
```

### 1.2 Servizio Tenant
```typescript
// src/app/shared/services/tenant.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Tenant } from '../models/tenant.model';

@Injectable({
  providedIn: 'root'
})
export class TenantService {
  private apiUrl = `${environment.apiUrl}/tenants`;

  constructor(private http: HttpClient) {}

  // Ottieni tutti i tenant con filtri opzionali
  getTenants(filters?: {
    search?: string;
    status?: 'active' | 'inactive';
    apartmentId?: number;
  }): Observable<Tenant[]> {
    let params = new HttpParams();
    
    if (filters?.search) {
      params = params.set('search', filters.search);
    }
    if (filters?.status) {
      params = params.set('status', filters.status);
    }
    if (filters?.apartmentId) {
      params = params.set('apartment_id', filters.apartmentId.toString());
    }

    return this.http.get<Tenant[]>(this.apiUrl, { params });
  }

  // Ottieni tenant per ID
  getTenantById(id: number): Observable<Tenant> {
    return this.http.get<Tenant>(`${this.apiUrl}/${id}`);
  }

  // Crea nuovo tenant
  createTenant(tenant: Omit<Tenant, 'id' | 'createdAt' | 'updatedAt'>): Observable<Tenant> {
    return this.http.post<Tenant>(this.apiUrl, tenant);
  }

  // Aggiorna tenant
  updateTenant(id: number, tenant: Partial<Tenant>): Observable<Tenant> {
    return this.http.put<Tenant>(`${this.apiUrl}/${id}`, tenant);
  }

  // Elimina tenant
  deleteTenant(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }

  // Cerca tenant per autocomplete
  searchTenants(query: string): Observable<Tenant[]> {
    return this.http.get<Tenant[]>(`${this.apiUrl}/search`, {
      params: { q: query }
    });
  }

  // Ottieni tenant attivi (con contratto attivo)
  getActiveTenants(): Observable<Tenant[]> {
    return this.http.get<Tenant[]>(`${this.apiUrl}/active`);
  }
}
```

## 2. Servizio Apartment

### 2.1 Interfaccia Apartment
```typescript
// src/app/shared/models/apartment.model.ts
export interface Apartment {
  id: number;
  name: string;
  address: string;
  floor: number;
  rooms: number;
  bathrooms: number;
  squareMeters: number;
  rent: number;
  deposit: number;
  utilities: {
    electricity: boolean;
    water: boolean;
    gas: boolean;
    heating: boolean;
    internet: boolean;
  };
  features: string[];
  status: 'available' | 'occupied' | 'maintenance' | 'reserved';
  currentTenantId?: number;
  images: ApartmentImage[];
  createdAt: Date;
  updatedAt: Date;
}

export interface ApartmentImage {
  id: number;
  url: string;
  caption?: string;
  isPrimary: boolean;
}
```

### 2.2 Servizio Apartment
```typescript
// src/app/shared/services/apartment.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Apartment } from '../models/apartment.model';

@Injectable({
  providedIn: 'root'
})
export class ApartmentService {
  private apiUrl = `${environment.apiUrl}/apartments`;

  constructor(private http: HttpClient) {}

  // Ottieni tutti gli appartamenti con filtri opzionali
  getApartments(filters?: {
    search?: string;
    status?: 'available' | 'occupied' | 'maintenance' | 'reserved';
    minRooms?: number;
    maxRent?: number;
  }): Observable<Apartment[]> {
    let params = new HttpParams();
    
    if (filters?.search) {
      params = params.set('search', filters.search);
    }
    if (filters?.status) {
      params = params.set('status', filters.status);
    }
    if (filters?.minRooms) {
      params = params.set('min_rooms', filters.minRooms.toString());
    }
    if (filters?.maxRent) {
      params = params.set('max_rent', filters.maxRent.toString());
    }

    return this.http.get<Apartment[]>(this.apiUrl, { params });
  }

  // Ottieni appartamento per ID
  getApartmentById(id: number): Observable<Apartment> {
    return this.http.get<Apartment>(`${this.apiUrl}/${id}`);
  }

  // Crea nuovo appartamento
  createApartment(apartment: Omit<Apartment, 'id' | 'createdAt' | 'updatedAt'>): Observable<Apartment> {
    return this.http.post<Apartment>(this.apiUrl, apartment);
  }

  // Aggiorna appartamento
  updateApartment(id: number, apartment: Partial<Apartment>): Observable<Apartment> {
    return this.http.put<Apartment>(`${this.apiUrl}/${id}`, apartment);
  }

  // Elimina appartamento
  deleteApartment(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }

  // Cerca appartamenti per autocomplete
  searchApartments(query: string): Observable<Apartment[]> {
    return this.http.get<Apartment[]>(`${this.apiUrl}/search`, {
      params: { q: query }
    });
  }

  // Ottieni appartamenti disponibili
  getAvailableApartments(): Observable<Apartment[]> {
    return this.http.get<Apartment[]>(`${this.apiUrl}/available`);
  }

  // Ottieni appartamenti occupati
  getOccupiedApartments(): Observable<Apartment[]> {
    return this.http.get<Apartment[]>(`${this.apiUrl}/occupied`);
  }

  // Aggiorna status appartamento
  updateApartmentStatus(id: number, status: Apartment['status']): Observable<Apartment> {
    return this.http.patch<Apartment>(`${this.apiUrl}/${id}/status`, { status });
  }
}
```

## 3. Aggiornamento dei Componenti

### 3.1 InvoiceFormComponent
Sostituire i dati mock con chiamate reali:

```typescript
// In invoice-form.component.ts
import { TenantService } from '../../../shared/services/tenant.service';
import { ApartmentService } from '../../../shared/services/apartment.service';

export class InvoiceFormComponent {
  constructor(
    // ... altri servizi
    private tenantService: TenantService,
    private apartmentService: ApartmentService
  ) {}

  private loadMockData(): void {
    // Sostituire con chiamate reali
    this.tenantService.getActiveTenants().subscribe(tenants => {
      this.tenants = tenants;
    });

    this.apartmentService.getOccupiedApartments().subscribe(apartments => {
      this.apartments = apartments;
    });
  }

  private setupAutocomplete(): void {
    // Autocomplete per inquilini
    this.filteredTenants = this.invoiceForm.get('tenantId')!.valueChanges.pipe(
      startWith(''),
      debounceTime(300),
      distinctUntilChanged(),
      switchMap(value => {
        if (typeof value === 'string' && value.length > 2) {
          return this.tenantService.searchTenants(value);
        }
        return of(this.tenants);
      })
    );

    // Autocomplete per appartamenti
    this.filteredApartments = this.invoiceForm.get('apartmentId')!.valueChanges.pipe(
      startWith(''),
      debounceTime(300),
      distinctUntilChanged(),
      switchMap(value => {
        if (typeof value === 'string' && value.length > 2) {
          return this.apartmentService.searchApartments(value);
        }
        return of(this.apartments);
      })
    );
  }
}
```

### 3.2 Altri Componenti
Aggiornare tutti i componenti che utilizzano `getTenantName()` e `getApartmentName()`:

```typescript
// Sostituire i metodi placeholder con chiamate reali
getTenantName(tenantId: number): string {
  const tenant = this.tenants.find(t => t.id === tenantId);
  return tenant ? tenant.name : `Inquilino ${tenantId}`;
}

getApartmentName(apartmentId: number): string {
  const apartment = this.apartments.find(a => a.id === apartmentId);
  return apartment ? apartment.name : `Appartamento ${apartmentId}`;
}
```

## 4. Backend API Endpoints

### 4.1 Tenant Endpoints
```php
// routes/api.php
Route::prefix('tenants')->group(function () {
    Route::get('/', [TenantController::class, 'index']);
    Route::get('/{id}', [TenantController::class, 'show']);
    Route::post('/', [TenantController::class, 'store']);
    Route::put('/{id}', [TenantController::class, 'update']);
    Route::delete('/{id}', [TenantController::class, 'destroy']);
    Route::get('/search', [TenantController::class, 'search']);
    Route::get('/active', [TenantController::class, 'active']);
});
```

### 4.2 Apartment Endpoints
```php
// routes/api.php
Route::prefix('apartments')->group(function () {
    Route::get('/', [ApartmentController::class, 'index']);
    Route::get('/{id}', [ApartmentController::class, 'show']);
    Route::post('/', [ApartmentController::class, 'store']);
    Route::put('/{id}', [ApartmentController::class, 'update']);
    Route::delete('/{id}', [ApartmentController::class, 'destroy']);
    Route::get('/search', [ApartmentController::class, 'search']);
    Route::get('/available', [ApartmentController::class, 'available']);
    Route::get('/occupied', [ApartmentController::class, 'occupied']);
    Route::patch('/{id}/status', [ApartmentController::class, 'updateStatus']);
});
```

## 5. Database Schema

### 5.1 Tabella Tenants
```sql
CREATE TABLE tenants (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    address TEXT,
    fiscal_code VARCHAR(20) UNIQUE,
    birth_date DATE,
    emergency_contact_name VARCHAR(255),
    emergency_contact_phone VARCHAR(50),
    emergency_contact_relationship VARCHAR(100),
    status ENUM('active', 'inactive') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_status (status)
);
```

### 5.2 Tabella Apartments
```sql
CREATE TABLE apartments (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL,
    floor INT,
    rooms INT NOT NULL,
    bathrooms INT NOT NULL,
    square_meters DECIMAL(8,2),
    rent DECIMAL(10,2) NOT NULL,
    deposit DECIMAL(10,2),
    utilities_electricity BOOLEAN DEFAULT FALSE,
    utilities_water BOOLEAN DEFAULT FALSE,
    utilities_gas BOOLEAN DEFAULT FALSE,
    utilities_heating BOOLEAN DEFAULT FALSE,
    utilities_internet BOOLEAN DEFAULT FALSE,
    features JSON,
    status ENUM('available', 'occupied', 'maintenance', 'reserved') DEFAULT 'available',
    current_tenant_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (current_tenant_id) REFERENCES tenants(id),
    INDEX idx_status (status),
    INDEX idx_current_tenant (current_tenant_id)
);
```

## 6. Implementazione Prioritaria

### 6.1 Fase 1 - Servizi Base
1. Creare i modelli `Tenant` e `Apartment`
2. Implementare i servizi base con dati mock
3. Aggiornare i componenti di fatturazione

### 6.2 Fase 2 - Backend
1. Creare le tabelle del database
2. Implementare i controller e i modelli Laravel
3. Configurare le API endpoints

### 6.3 Fase 3 - Integrazione Completa
1. Sostituire i dati mock con chiamate reali
2. Implementare autocomplete avanzato
3. Aggiungere validazioni e gestione errori

## 7. Vantaggi dell'Implementazione

- **Dati Reali**: I componenti di fatturazione utilizzeranno dati reali di tenant e appartamenti
- **Autocomplete Intelligente**: Ricerca avanzata per tenant e appartamenti
- **Validazione**: Controlli sui dati inseriti
- **Performance**: Caching e ottimizzazioni per grandi volumi di dati
- **Scalabilità**: Architettura pronta per future espansioni

## 8. Note per lo Sviluppo

- Implementare prima i servizi con dati mock per testare l'interfaccia
- Aggiungere gestione degli errori e loading states
- Considerare l'implementazione di cache per migliorare le performance
- Aggiungere test unitari per i servizi
- Documentare le API per il team di sviluppo 