# Modifiche Frontend per Sistema di Fatturazione

## Panoramica
Questo documento descrive tutte le modifiche necessarie al frontend Angular per integrare il sistema di fatturazione completo con il backend FastAPI.

## 1. Aggiornamento GenericApiService

Il `GenericApiService` è già configurato per supportare tutte le operazioni CRUD standard. Assicurarsi che sia configurato correttamente:

```typescript
// src/app/services/generic-api.service.ts
// Verificare che il service supporti tutti i metodi necessari:
// - getAll<T>(entity: string, params?: any)
// - getById<T>(entity: string, id: number)
// - create<T>(entity: string, data: any)
// - update<T>(entity: string, id: number, data: any)
// - delete(entity: string, id: number)
// - invalidateCache(entity: string, id?: number)
```

## 2. Creazione InvoiceService

Creare un nuovo service dedicato alle fatture o controllare se va modificato:

```typescript
// src/app/services/invoice.service.ts
import { Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { GenericApiService } from './generic-api.service';
import { Invoice, InvoiceCreate, PaymentRecord } from '../models/invoice.model';

@Injectable({
  providedIn: 'root'
})
export class InvoiceService {
  private apiUrl = 'invoices';

  constructor(private apiService: GenericApiService) {}

  // Metodi CRUD standard
  getAllInvoices(params?: any): Observable<Invoice[]> {
    return this.apiService.getAll<Invoice>(this.apiUrl, params).pipe(
      catchError(error => {
        console.error('Errore nel recupero delle fatture:', error);
        return throwError(() => new Error('Impossibile recuperare le fatture dal database'));
      })
    );
  }

  getInvoiceById(id: number): Observable<Invoice> {
    return this.apiService.getById<Invoice>(this.apiUrl, id).pipe(
      catchError(error => {
        console.error(`Errore nel recupero della fattura ${id}:`, error);
        return throwError(() => new Error(`Fattura con ID ${id} non trovata`));
      })
    );
  }

  createInvoice(invoice: Partial<InvoiceCreate>): Observable<Invoice> {
    return this.apiService.create<Invoice>(this.apiUrl, invoice).pipe(
      tap(() => this.apiService.invalidateCache(this.apiUrl)),
      catchError(error => {
        console.error('Errore nella creazione della fattura:', error);
        return throwError(() => new Error('Impossibile creare la fattura'));
      })
    );
  }

  updateInvoice(id: number, invoice: Partial<InvoiceCreate>): Observable<Invoice> {
    return this.apiService.update<Invoice>(this.apiUrl, id, invoice).pipe(
      tap(() => this.apiService.invalidateCache(this.apiUrl, id)),
      catchError(error => {
        console.error(`Errore nell'aggiornamento della fattura ${id}:`, error);
        return throwError(() => new Error(`Impossibile aggiornare la fattura ${id}`));
      })
    );
  }

  deleteInvoice(id: number): Observable<void> {
    return this.apiService.delete(this.apiUrl, id).pipe(
      tap(() => this.apiService.invalidateCache(this.apiUrl, id)),
      catchError(error => {
        console.error(`Errore nell'eliminazione della fattura ${id}:`, error);
        return throwError(() => new Error(`Impossibile eliminare la fattura ${id}`));
      })
    );
  }

  // Metodi specifici per fatturazione
  markAsPaid(invoiceId: number, paymentData: any): Observable<Invoice> {
    return this.apiService.post<Invoice>(`${this.apiUrl}/${invoiceId}/mark-as-paid`, paymentData);
  }

  addPaymentRecord(invoiceId: number, paymentRecord: PaymentRecord): Observable<PaymentRecord> {
    return this.apiService.post<PaymentRecord>(`${this.apiUrl}/${invoiceId}/payment-records`, paymentRecord);
  }

  getPaymentRecords(invoiceId: number): Observable<PaymentRecord[]> {
    return this.apiService.getAll<PaymentRecord>(`${this.apiUrl}/${invoiceId}/payment-records`);
  }

  sendReminder(invoiceId: number, reminderData: any): Observable<any> {
    return this.apiService.post<any>(`${this.apiUrl}/${invoiceId}/send-reminder`, reminderData);
  }

  getOverdueInvoices(daysOverdue?: number): Observable<Invoice[]> {
    const params = daysOverdue ? { days_overdue: daysOverdue } : {};
    return this.apiService.getAll<Invoice>(`${this.apiUrl}/overdue`, params);
  }

  generateMonthlyInvoices(data: any): Observable<any> {
    return this.apiService.post<any>(`${this.apiUrl}/generate-monthly`, data);
  }

  generateFromLease(data: any): Observable<any> {
    return this.apiService.post<any>(`${this.apiUrl}/generate-from-lease`, data);
  }

  getStatistics(period?: string): Observable<any> {
    const params = period ? { period } : {};
    return this.apiService.getAll<any>(`${this.apiUrl}/statistics`, params);
  }

  generatePdf(invoiceId: number, options?: any): Observable<Blob> {
    const params = options ? { ...options } : {};
    return this.apiService.getBlob(`${this.apiUrl}/${invoiceId}/pdf`, params);
  }

  sendBulkReminders(data: any): Observable<any> {
    return this.apiService.post<any>(`${this.apiUrl}/send-bulk-reminders`, data);
  }

  // Integrazione con entità esistenti
  getActiveTenants(): Observable<any[]> {
    return this.apiService.getAll<any>('tenants', { status: 'active' });
  }

  getOccupiedApartments(): Observable<any[]> {
    return this.apiService.getAll<any>('apartments', { status: 'occupied' });
  }

  getActiveLeases(): Observable<any[]> {
    return this.apiService.getAll<any>('leases', { status: 'active' });
  }

  getUtilityReadings(apartmentId: number, params: any): Observable<any[]> {
    return this.apiService.getAll<any>('utilities', { apartmentId, ...params });
  }
}
```

## 3. Modelli TypeScript

Creare i modelli TypeScript per le fatture:

```typescript
// src/app/models/invoice.model.ts
export interface Invoice {
  id: number;
  leaseId: number;
  tenantId: number;
  apartmentId: number;
  invoiceNumber: string;
  month: number;
  year: number;
  issueDate: string;
  dueDate: string;
  subtotal: number;
  tax: number;
  total: number;
  isPaid: boolean;
  paymentDate?: string;
  paymentMethod?: string;
  notes?: string;
  reminderSent: boolean;
  reminderDate?: string;
  createdAt: string;
  updatedAt: string;
  items: InvoiceItem[];
  payments: PaymentRecord[];
  tenant?: Tenant;
  apartment?: Apartment;
  lease?: Lease;
}

export interface InvoiceItem {
  id: number;
  invoiceId: number;
  description: string;
  amount: number;
  type: string;
  createdAt: string;
  updatedAt: string;
}

export interface PaymentRecord {
  id: number;
  invoiceId: number;
  amount: number;
  paymentDate: string;
  paymentMethod: string;
  reference?: string;
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

export interface InvoiceCreate {
  leaseId: number;
  tenantId: number;
  apartmentId: number;
  invoiceNumber?: string;
  month: number;
  year: number;
  issueDate: string;
  dueDate: string;
  notes?: string;
  items: InvoiceItemCreate[];
}

export interface InvoiceItemCreate {
  invoiceId?: number;
  description: string;
  amount: number;
  type: string;
}

export interface PaymentRecordCreate {
  invoiceId?: number;
  amount: number;
  paymentDate: string;
  paymentMethod: string;
  reference?: string;
  notes?: string;
}

export interface InvoiceStatistics {
  totalInvoiced: number;
  totalPaid: number;
  totalUnpaid: number;
  overdueInvoices: number;
  thisMonthInvoices: number;
  period: string;
  startDate: string;
  endDate: string;
}

export interface InvoiceFilters {
  status?: string;
  tenantId?: number;
  apartmentId?: number;
  leaseId?: number;
  month?: number;
  year?: number;
  startDate?: string;
  endDate?: string;
  search?: string;
  sortBy?: string;
  sortOrder?: string;
  page?: number;
  limit?: number;
}

// Interfacce per entità correlate
export interface Tenant {
  id: number;
  firstName: string;
  lastName: string;
  email?: string;
  phone: string;
  // ... altri campi
}

export interface Apartment {
  id: number;
  name: string;
  description?: string;
  // ... altri campi
}

export interface Lease {
  id: number;
  tenantId: number;
  apartmentId: number;
  startDate: string;
  endDate: string;
  monthlyRent: number;
  // ... altri campi
}
```

## 4. Componenti Angular

### 4.1 Lista Fatture

```typescript
// src/app/components/invoice-list/invoice-list.component.ts
import { Component, OnInit } from '@angular/core';
import { InvoiceService } from '../../services/invoice.service';
import { Invoice, InvoiceFilters } from '../../models/invoice.model';

@Component({
  selector: 'app-invoice-list',
  templateUrl: './invoice-list.component.html',
  styleUrls: ['./invoice-list.component.scss']
})
export class InvoiceListComponent implements OnInit {
  invoices: Invoice[] = [];
  loading = false;
  error = '';
  filters: InvoiceFilters = {};
  
  constructor(private invoiceService: InvoiceService) {}

  ngOnInit(): void {
    this.loadInvoices();
  }

  loadInvoices(): void {
    this.loading = true;
    this.error = '';
    
    this.invoiceService.getAllInvoices(this.filters).subscribe({
      next: (invoices) => {
        this.invoices = invoices;
        this.loading = false;
      },
      error: (error) => {
        this.error = error.message;
        this.loading = false;
      }
    });
  }

  onFilterChange(filters: InvoiceFilters): void {
    this.filters = { ...filters };
    this.loadInvoices();
  }

  onDeleteInvoice(id: number): void {
    if (confirm('Sei sicuro di voler eliminare questa fattura?')) {
      this.invoiceService.deleteInvoice(id).subscribe({
        next: () => {
          this.loadInvoices();
        },
        error: (error) => {
          this.error = error.message;
        }
      });
    }
  }

  onMarkAsPaid(invoice: Invoice): void {
    const paymentData = {
      payment_date: new Date().toISOString().split('T')[0],
      payment_method: 'bank_transfer'
    };

    this.invoiceService.markAsPaid(invoice.id, paymentData).subscribe({
      next: (updatedInvoice) => {
        const index = this.invoices.findIndex(i => i.id === invoice.id);
        if (index !== -1) {
          this.invoices[index] = updatedInvoice;
        }
      },
      error: (error) => {
        this.error = error.message;
      }
    });
  }

  onSendReminder(invoice: Invoice): void {
    const reminderData = {
      send_via: 'whatsapp',
      message: 'Promemoria pagamento fattura'
    };

    this.invoiceService.sendReminder(invoice.id, reminderData).subscribe({
      next: (result) => {
        console.log('Promemoria inviato:', result);
        // Aggiorna lo stato della fattura
        this.loadInvoices();
      },
      error: (error) => {
        this.error = error.message;
      }
    });
  }
}
```

### 4.2 Template Lista Fatture

```html
<!-- src/app/components/invoice-list/invoice-list.component.html -->
<div class="invoice-list-container">
  <div class="header">
    <h2>Gestione Fatture</h2>
    <button mat-raised-button color="primary" routerLink="/invoices/new">
      <mat-icon>add</mat-icon>
      Nuova Fattura
    </button>
  </div>

  <!-- Filtri -->
  <app-invoice-filters 
    [filters]="filters"
    (filtersChange)="onFilterChange($event)">
  </app-invoice-filters>

  <!-- Messaggio di errore -->
  <div *ngIf="error" class="error-message">
    {{ error }}
  </div>

  <!-- Loading -->
  <div *ngIf="loading" class="loading">
    <mat-spinner></mat-spinner>
  </div>

  <!-- Lista fatture -->
  <div *ngIf="!loading && invoices.length > 0" class="invoice-grid">
    <mat-card *ngFor="let invoice of invoices" class="invoice-card">
      <mat-card-header>
        <mat-card-title>{{ invoice.invoiceNumber }}</mat-card-title>
        <mat-card-subtitle>
          {{ invoice.tenant?.firstName }} {{ invoice.tenant?.lastName }} - 
          {{ invoice.apartment?.name }}
        </mat-card-subtitle>
        <div class="status-badge" [class]="getStatusClass(invoice)">
          {{ getStatusText(invoice) }}
        </div>
      </mat-card-header>

      <mat-card-content>
        <div class="invoice-details">
          <p><strong>Periodo:</strong> {{ invoice.month }}/{{ invoice.year }}</p>
          <p><strong>Scadenza:</strong> {{ invoice.dueDate | date:'dd/MM/yyyy' }}</p>
          <p><strong>Totale:</strong> €{{ invoice.total | number:'1.2-2' }}</p>
        </div>
      </mat-card-content>

      <mat-card-actions>
        <button mat-button [routerLink]="['/invoices', invoice.id]">
          <mat-icon>visibility</mat-icon>
          Visualizza
        </button>
        
        <button mat-button [routerLink]="['/invoices', invoice.id, 'edit']">
          <mat-icon>edit</mat-icon>
          Modifica
        </button>

        <button *ngIf="!invoice.isPaid" 
                mat-button 
                color="primary"
                (click)="onMarkAsPaid(invoice)">
          <mat-icon>payment</mat-icon>
          Segna come Pagata
        </button>

        <button *ngIf="!invoice.isPaid" 
                mat-button 
                color="accent"
                (click)="onSendReminder(invoice)">
          <mat-icon>notifications</mat-icon>
          Invia Promemoria
        </button>

        <button mat-button 
                color="warn"
                (click)="onDeleteInvoice(invoice.id)">
          <mat-icon>delete</mat-icon>
          Elimina
        </button>
      </mat-card-actions>
    </mat-card>
  </div>

  <!-- Nessuna fattura -->
  <div *ngIf="!loading && invoices.length === 0" class="no-invoices">
    <mat-icon>receipt</mat-icon>
    <p>Nessuna fattura trovata</p>
  </div>
</div>
```

### 4.3 Form Fattura

```typescript
// src/app/components/invoice-form/invoice-form.component.ts
import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { InvoiceService } from '../../services/invoice.service';
import { InvoiceCreate, InvoiceItemCreate } from '../../models/invoice.model';

@Component({
  selector: 'app-invoice-form',
  templateUrl: './invoice-form.component.html',
  styleUrls: ['./invoice-form.component.scss']
})
export class InvoiceFormComponent implements OnInit {
  invoiceForm: FormGroup;
  itemsForm: FormGroup;
  loading = false;
  error = '';
  isEditMode = false;
  invoiceId?: number;

  tenants: any[] = [];
  apartments: any[] = [];
  leases: any[] = [];

  constructor(
    private fb: FormBuilder,
    private invoiceService: InvoiceService,
    private route: ActivatedRoute,
    private router: Router
  ) {
    this.invoiceForm = this.fb.group({
      leaseId: ['', Validators.required],
      tenantId: ['', Validators.required],
      apartmentId: ['', Validators.required],
      month: ['', [Validators.required, Validators.min(1), Validators.max(12)]],
      year: ['', [Validators.required, Validators.min(2020)]],
      issueDate: ['', Validators.required],
      dueDate: ['', Validators.required],
      notes: ['']
    });

    this.itemsForm = this.fb.group({
      items: this.fb.array([])
    });
  }

  ngOnInit(): void {
    this.loadData();
    
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEditMode = true;
      this.invoiceId = +id;
      this.loadInvoice(this.invoiceId);
    }
  }

  loadData(): void {
    // Carica tenant, appartamenti e contratti
    this.invoiceService.getActiveTenants().subscribe(tenants => {
      this.tenants = tenants;
    });

    this.invoiceService.getOccupiedApartments().subscribe(apartments => {
      this.apartments = apartments;
    });

    this.invoiceService.getActiveLeases().subscribe(leases => {
      this.leases = leases;
    });
  }

  loadInvoice(id: number): void {
    this.loading = true;
    this.invoiceService.getInvoiceById(id).subscribe({
      next: (invoice) => {
        this.invoiceForm.patchValue({
          leaseId: invoice.leaseId,
          tenantId: invoice.tenantId,
          apartmentId: invoice.apartmentId,
          month: invoice.month,
          year: invoice.year,
          issueDate: invoice.issueDate,
          dueDate: invoice.dueDate,
          notes: invoice.notes
        });
        
        // Carica gli items
        this.loadItems(invoice.items);
        this.loading = false;
      },
      error: (error) => {
        this.error = error.message;
        this.loading = false;
      }
    });
  }

  onSubmit(): void {
    if (this.invoiceForm.valid && this.itemsForm.valid) {
      this.loading = true;
      
      const invoiceData: InvoiceCreate = {
        ...this.invoiceForm.value,
        items: this.getItemsArray()
      };

      const request = this.isEditMode && this.invoiceId
        ? this.invoiceService.updateInvoice(this.invoiceId, invoiceData)
        : this.invoiceService.createInvoice(invoiceData);

      request.subscribe({
        next: (invoice) => {
          this.router.navigate(['/invoices', invoice.id]);
        },
        error: (error) => {
          this.error = error.message;
          this.loading = false;
        }
      });
    }
  }

  addItem(): void {
    const items = this.itemsForm.get('items') as any;
    items.push(this.fb.group({
      description: ['', Validators.required],
      amount: ['', [Validators.required, Validators.min(0)]],
      type: ['rent', Validators.required]
    }));
  }

  removeItem(index: number): void {
    const items = this.itemsForm.get('items') as any;
    items.removeAt(index);
  }

  private getItemsArray(): InvoiceItemCreate[] {
    const items = this.itemsForm.get('items')?.value || [];
    return items.map((item: any) => ({
      description: item.description,
      amount: item.amount,
      type: item.type
    }));
  }

  private loadItems(items: any[]): void {
    const itemsArray = this.itemsForm.get('items') as any;
    itemsArray.clear();
    
    items.forEach(item => {
      itemsArray.push(this.fb.group({
        description: [item.description, Validators.required],
        amount: [item.amount, [Validators.required, Validators.min(0)]],
        type: [item.type, Validators.required]
      }));
    });
  }
}
```

## 5. Routing

Aggiornare il routing per includere le fatture:

```typescript
// src/app/app-routing.module.ts
const routes: Routes = [
  // ... routes esistenti
  {
    path: 'invoices',
    children: [
      { path: '', component: InvoiceListComponent },
      { path: 'new', component: InvoiceFormComponent },
      { path: ':id', component: InvoiceDetailComponent },
      { path: ':id/edit', component: InvoiceFormComponent },
      { path: 'statistics', component: InvoiceStatisticsComponent }
    ]
  }
];
```

## 6. Menu di Navigazione

Aggiornare il menu per includere la sezione fatture:

```html
<!-- src/app/components/nav-menu/nav-menu.component.html -->
<mat-nav-list>
  <!-- ... menu items esistenti -->
  
  <a mat-list-item routerLink="/invoices" routerLinkActive="active">
    <mat-icon>receipt</mat-icon>
    <span>Fatture</span>
  </a>
  
  <a mat-list-item routerLink="/invoices/statistics" routerLinkActive="active">
    <mat-icon>analytics</mat-icon>
    <span>Statistiche Fatture</span>
  </a>
</mat-nav-list>
```

## 7. Dashboard Integration

Aggiornare il dashboard per mostrare statistiche fatture:

```typescript
// src/app/components/dashboard/dashboard.component.ts
export class DashboardComponent implements OnInit {
  invoiceStats: InvoiceStatistics | null = null;

  constructor(private invoiceService: InvoiceService) {}

  ngOnInit(): void {
    this.loadInvoiceStatistics();
  }

  loadInvoiceStatistics(): void {
    this.invoiceService.getStatistics('this_month').subscribe({
      next: (stats) => {
        this.invoiceStats = stats;
      },
      error: (error) => {
        console.error('Errore nel caricamento statistiche fatture:', error);
      }
    });
  }
}
```

## 8. Gestione Errori

Implementare una gestione errori centralizzata:

```typescript
// src/app/interceptors/error.interceptor.ts
import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { MatSnackBar } from '@angular/material/snack-bar';

@Injectable()
export class ErrorInterceptor implements HttpInterceptor {
  constructor(private snackBar: MatSnackBar) {}

  intercept(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    return next.handle(request).pipe(
      catchError((error: HttpErrorResponse) => {
        let errorMessage = 'Si è verificato un errore';
        
        if (error.error instanceof ErrorEvent) {
          // Client-side error
          errorMessage = error.error.message;
        } else {
          // Server-side error
          errorMessage = error.error?.detail || error.message;
        }
        
        this.snackBar.open(errorMessage, 'Chiudi', {
          duration: 5000,
          panelClass: ['error-snackbar']
        });
        
        return throwError(() => new Error(errorMessage));
      })
    );
  }
}
```

## 9. Stili CSS

Aggiungere stili per i componenti fatture:

```scss
// src/app/components/invoice-list/invoice-list.component.scss
.invoice-list-container {
  padding: 20px;
  
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }
  
  .invoice-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
    gap: 20px;
  }
  
  .invoice-card {
    .status-badge {
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: bold;
      
      &.paid {
        background-color: #4caf50;
        color: white;
      }
      
      &.unpaid {
        background-color: #ff9800;
        color: white;
      }
      
      &.overdue {
        background-color: #f44336;
        color: white;
      }
    }
  }
  
  .no-invoices {
    text-align: center;
    padding: 40px;
    color: #666;
    
    mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      margin-bottom: 16px;
    }
  }
}
```

## 10. Testing

Creare test unitari per i componenti:

```typescript
// src/app/components/invoice-list/invoice-list.component.spec.ts
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { InvoiceListComponent } from './invoice-list.component';
import { InvoiceService } from '../../services/invoice.service';
import { of, throwError } from 'rxjs';

describe('InvoiceListComponent', () => {
  let component: InvoiceListComponent;
  let fixture: ComponentFixture<InvoiceListComponent>;
  let mockInvoiceService: jasmine.SpyObj<InvoiceService>;

  beforeEach(async () => {
    const spy = jasmine.createSpyObj('InvoiceService', ['getAllInvoices']);
    
    await TestBed.configureTestingModule({
      declarations: [ InvoiceListComponent ],
      providers: [
        { provide: InvoiceService, useValue: spy }
      ]
    }).compileComponents();

    mockInvoiceService = TestBed.inject(InvoiceService) as jasmine.SpyObj<InvoiceService>;
  });

  it('should load invoices on init', () => {
    const mockInvoices = [
      { id: 1, invoiceNumber: 'INV-2024-001', total: 1000 }
    ];
    mockInvoiceService.getAllInvoices.and.returnValue(of(mockInvoices));

    fixture = TestBed.createComponent(InvoiceListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.invoices).toEqual(mockInvoices);
    expect(mockInvoiceService.getAllInvoices).toHaveBeenCalled();
  });

  it('should handle error when loading invoices', () => {
    mockInvoiceService.getAllInvoices.and.returnValue(
      throwError(() => new Error('Errore di rete'))
    );

    fixture = TestBed.createComponent(InvoiceListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.error).toBe('Errore di rete');
  });
});
```

## 11. Deployment Checklist

- [ ] Verificare che tutti i componenti siano dichiarati nei moduli
- [ ] Testare tutti gli endpoint API
- [ ] Verificare la gestione errori
- [ ] Testare la navigazione tra le pagine
- [ ] Verificare la responsività del design
- [ ] Testare la generazione PDF
- [ ] Verificare l'invio promemoria
- [ ] Testare la generazione automatica fatture
- [ ] Verificare le statistiche e KPI
- [ ] Testare l'integrazione con tenant, apartment, lease

## 12. Note Importanti

1. **Gestione Errori**: Tutti i metodi utilizzano `throwError` invece di fallback ai dati mock
2. **Cache**: Il `GenericApiService` gestisce automaticamente l'invalidazione della cache
3. **Type Safety**: Tutti i modelli sono tipizzati con TypeScript
4. **Responsive Design**: I componenti sono progettati per essere responsive
5. **Accessibilità**: Utilizzare le direttive Angular Material per l'accessibilità
6. **Performance**: Implementare lazy loading per i moduli se necessario
7. **Security**: Tutte le chiamate API includono l'header di autorizzazione
8. **Testing**: Creare test unitari e di integrazione per tutti i componenti

## 13. Configurazione Ambiente

Assicurarsi che le variabili d'ambiente siano configurate correttamente:

```bash
# .env
API_BASE_URL=http://localhost:8000
ENABLE_INVOICE_FEATURES=true
DEFAULT_CURRENCY=EUR
DEFAULT_TAX_RATE=22
```

## 14. Supporto e Manutenzione

- Monitoraggio continuo delle performance
- Aggiornamenti di sicurezza
- Backup automatici
- Supporto tecnico per integrazione
- Training per il personale
- Documentazione API aggiornata
- Monitoraggio errori reali
- Ottimizzazione query database
- Monitoraggio efficienza cache 