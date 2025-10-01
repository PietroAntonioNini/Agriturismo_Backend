# Modifiche Backend per Sistema di Fatturazione - AGGIORNATO

## Panoramica
Questo documento descrive tutte le modifiche necessarie al backend per supportare il sistema di fatturazione completo, ottimizzato per l'integrazione con SendPulse per l'invio di messaggi WhatsApp.

## IMPORTANTE: Integrazione con Frontend Angular
Il frontend Angular utilizza il `GenericApiService` per tutte le chiamate API. Le seguenti modifiche devono essere compatibili con questo pattern:

- Endpoint base: `/api/{entity}/`
- Metodi supportati: GET, POST, PUT, DELETE, PATCH
- Gestione automatica dei parametri di query
- Supporto per upload file con FormData
- Cache intelligente lato frontend
- Gestione errori centralizzata

## 1. Modelli di Dati

### 1.1 Modello Invoice
```sql
CREATE TABLE invoices (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    lease_id BIGINT NOT NULL, -- AGGIUNTO: riferimento al contratto
    tenant_id BIGINT NOT NULL,
    apartment_id BIGINT NOT NULL,
    month INT NOT NULL CHECK (month >= 1 AND month <= 12),
    year INT NOT NULL,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    period_start DATE NOT NULL, -- AGGIUNTO: inizio periodo fatturazione
    period_end DATE NOT NULL, -- AGGIUNTO: fine periodo fatturazione
    subtotal DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    tax DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    is_paid BOOLEAN DEFAULT FALSE,
    status ENUM('pending', 'paid', 'overdue', 'cancelled') DEFAULT 'pending', -- AGGIUNTO: status
    payment_date DATE NULL,
    payment_method ENUM('cash', 'bank_transfer', 'credit_card', 'check') NULL,
    reminder_sent BOOLEAN DEFAULT FALSE,
    reminder_date DATETIME NULL,
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (lease_id) REFERENCES leases(id) ON DELETE CASCADE, -- AGGIUNTO
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (apartment_id) REFERENCES apartments(id) ON DELETE CASCADE,
    
    INDEX idx_lease_tenant_apartment (lease_id, tenant_id, apartment_id),
    INDEX idx_period (month, year),
    INDEX idx_status (is_paid, status),
    INDEX idx_due_date (due_date),
    INDEX idx_invoice_number (invoice_number),
    INDEX idx_period_dates (period_start, period_end)
);
```

### 1.2 Modello InvoiceItem
```sql
CREATE TABLE invoice_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    invoice_id BIGINT NOT NULL,
    type ENUM('rent', 'electricity', 'water', 'gas', 'maintenance', 'other') NOT NULL,
    description VARCHAR(255) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL DEFAULT 1.00, -- AGGIUNTO: quantità
    unit_price DECIMAL(10,2) NOT NULL, -- AGGIUNTO: prezzo unitario
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    
    INDEX idx_invoice_id (invoice_id),
    INDEX idx_type (type),
    INDEX idx_invoice_type (invoice_id, type)
);
```

### 1.3 Modello PaymentRecord
```sql
CREATE TABLE payment_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    invoice_id BIGINT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_date DATE NOT NULL,
    payment_method ENUM('cash', 'bank_transfer', 'credit_card', 'check') NOT NULL,
    reference VARCHAR(100) NULL,
    notes TEXT NULL,
    status ENUM('completed', 'pending', 'failed') DEFAULT 'completed', -- AGGIUNTO: status pagamento
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, -- AGGIUNTO: updated_at
    
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    
    INDEX idx_invoice_id (invoice_id),
    INDEX idx_payment_date (payment_date),
    INDEX idx_status (status),
    INDEX idx_payment_method (payment_method)
);
```

## 2. Integrazione con Servizi Esistenti

### 2.1 Compatibilità con GenericApiService
Il frontend Angular utilizza il `GenericApiService` che supporta i seguenti pattern:

```typescript
// Pattern standard per tutte le entità
GET    /api/invoices/                    // Lista con filtri
GET    /api/invoices/{id}                // Dettaglio singolo
POST   /api/invoices/                    // Creazione
PUT    /api/invoices/{id}                // Aggiornamento completo
PATCH  /api/invoices/{id}                // Aggiornamento parziale
DELETE /api/invoices/{id}                // Eliminazione

// Parametri di query supportati automaticamente
?status=paid&month=6&year=2024&tenant_id=1&page=1&limit=10&sort_by=issue_date&sort_order=desc

// Ricerca testuale
GET /api/invoices/search?q=INV-2024-001

// Relazioni (se supportate dal backend)
GET /api/invoices/{id}/items
GET /api/invoices/{id}/payment-records
```

### 2.2 Endpoint Specifici per Fatturazione
Oltre agli endpoint standard, sono necessari endpoint specifici per funzionalità avanzate.

### 2.3 Integrazione con Entità Esistenti
Il sistema di fatturazione deve integrarsi con le entità esistenti:

#### Tenant Integration
```typescript
// Endpoint per ottenere tenant con contratti attivi
GET /api/tenants?status=active&has_active_lease=true

// Endpoint per ottenere tenant con fatture
GET /api/tenants/{id}/invoices

// Endpoint per ottenere storico pagamenti tenant
GET /api/tenants/{id}/payment-history
```

#### Apartment Integration
```typescript
// Endpoint per ottenere appartamenti occupati
GET /api/apartments?status=occupied

// Endpoint per ottenere fatture di un appartamento
GET /api/apartments/{id}/invoices

// Endpoint per ottenere letture utility di un appartamento
GET /api/apartments/{id}/utility-readings
```

#### Lease Integration
```typescript
// Endpoint per ottenere contratti attivi
GET /api/leases?status=active

// Endpoint per ottenere fatture di un contratto
GET /api/leases/{id}/invoices

// Endpoint per generare fattura automatica da contratto
POST /api/leases/{id}/generate-invoice
```

#### Utility Integration
```typescript
// Endpoint per ottenere letture utility per periodo
GET /api/utilities?apartment_id={id}&start_date={date}&end_date={date}

// Endpoint per calcolare costi utility per periodo
GET /api/utilities/calculate-costs?apartment_id={id}&period_start={date}&period_end={date}

// Endpoint per generare voci fattura da letture utility
POST /api/utilities/generate-invoice-items
```

## 3. API Endpoints

### 3.1 Gestione Fatture

#### GET /api/invoices
Recupera tutte le fatture con filtri opzionali
```json
{
  "endpoint": "/api/invoices",
  "method": "GET",
  "query_params": {
    "status": "all|paid|unpaid|overdue",
    "period": "all|this_month|last_month|this_year|custom",
    "tenant_id": "number",
    "apartment_id": "number",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "search": "string",
    "page": "number",
    "limit": "number",
    "sort_by": "issue_date|due_date|total|invoice_number",
    "sort_order": "asc|desc"
  },
  "response": {
    "data": [
      {
        "id": 1,
        "invoice_number": "INV-2024-001",
        "tenant_id": 1,
        "apartment_id": 1,
        "month": 1,
        "year": 2024,
        "issue_date": "2024-01-01",
        "due_date": "2024-01-31",
        "subtotal": 800.00,
        "tax": 176.00,
        "total": 976.00,
        "is_paid": false,
        "payment_date": null,
        "payment_method": null,
        "reminder_sent": false,
        "reminder_date": null,
        "notes": null,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "items": [
          {
            "id": 1,
            "type": "rent",
            "description": "Affitto mensile",
            "amount": 800.00
          }
        ],
        "tenant": {
          "id": 1,
          "name": "Mario Rossi",
          "email": "mario.rossi@email.com"
        },
        "apartment": {
          "id": 1,
          "name": "Appartamento A",
          "address": "Via Roma 1"
        }
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 10,
      "total": 100,
      "total_pages": 10
    }
  }
}
```

#### GET /api/invoices/{id}
Recupera una singola fattura
```json
{
  "endpoint": "/api/invoices/{id}",
  "method": "GET",
  "response": {
    "id": 1,
    "invoice_number": "INV-2024-001",
    "tenant_id": 1,
    "apartment_id": 1,
    "month": 1,
    "year": 2024,
    "issue_date": "2024-01-01",
    "due_date": "2024-01-31",
    "subtotal": 800.00,
    "tax": 176.00,
    "total": 976.00,
    "is_paid": false,
    "payment_date": null,
    "payment_method": null,
    "reminder_sent": false,
    "reminder_date": null,
    "notes": null,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "items": [...],
    "tenant": {...},
    "apartment": {...},
    "payment_records": [...]
  }
}
```

#### POST /api/invoices
Crea una nuova fattura
```json
{
  "endpoint": "/api/invoices",
  "method": "POST",
  "body": {
    "tenant_id": 1,
    "apartment_id": 1,
    "month": 1,
    "year": 2024,
    "issue_date": "2024-01-01",
    "due_date": "2024-01-31",
    "notes": "Fattura per gennaio 2024",
    "items": [
      {
        "type": "rent",
        "description": "Affitto mensile",
        "amount": 800.00
      },
      {
        "type": "electricity",
        "description": "Consumo elettricità",
        "amount": 50.00
      }
    ]
  },
  "response": {
    "id": 1,
    "invoice_number": "INV-2024-001",
    "message": "Fattura creata con successo"
  }
}
```

#### PUT /api/invoices/{id}
Aggiorna una fattura
```json
{
  "endpoint": "/api/invoices/{id}",
  "method": "PUT",
  "body": {
    "due_date": "2024-02-15",
    "notes": "Fattura aggiornata",
    "items": [...]
  }
}
```

#### DELETE /api/invoices/{id}
Elimina una fattura
```json
{
  "endpoint": "/api/invoices/{id}",
  "method": "DELETE",
  "response": {
    "message": "Fattura eliminata con successo"
  }
}
```

#### POST /api/invoices/generate-monthly
Genera fatture mensili automatiche
```json
{
  "endpoint": "/api/invoices/generate-monthly",
  "method": "POST",
  "body": {
    "month": 6,
    "year": 2024,
    "include_utilities": true,
    "send_notifications": true
  },
  "response": {
    "generated_count": 5,
    "total_amount": 4500.00,
    "message": "Fatture mensili generate con successo"
  }
}
```

#### POST /api/invoices/generate-from-lease
Genera fattura da contratto specifico
```json
{
  "endpoint": "/api/invoices/generate-from-lease",
  "method": "POST",
  "body": {
    "lease_id": 1,
    "month": 6,
    "year": 2024,
    "include_utilities": true,
    "custom_items": [
      {
        "type": "maintenance",
        "description": "Riparazione caldaia",
        "amount": 150.00
      }
    ]
  },
  "response": {
    "invoice_id": 123,
    "invoice_number": "INV-2024-006",
    "total": 950.00,
    "message": "Fattura generata con successo"
  }
}
```

### 2.2 Gestione Pagamenti

#### POST /api/invoices/{id}/mark-as-paid
Marca una fattura come pagata
```json
{
  "endpoint": "/api/invoices/{id}/mark-as-paid",
  "method": "POST",
  "body": {
    "payment_date": "2024-01-15",
    "payment_method": "bank_transfer"
  },
  "response": {
    "message": "Fattura marcata come pagata",
    "invoice": {...}
  }
}
```

#### POST /api/invoices/{id}/payment-records
Registra un pagamento parziale
```json
{
  "endpoint": "/api/invoices/{id}/payment-records",
  "method": "POST",
  "body": {
    "amount": 500.00,
    "payment_date": "2024-01-15",
    "payment_method": "bank_transfer",
    "reference": "BON-2024-001",
    "notes": "Pagamento parziale"
  }
}
```

#### GET /api/invoices/{id}/payment-records
Recupera i record di pagamento di una fattura
```json
{
  "endpoint": "/api/invoices/{id}/payment-records",
  "method": "GET",
  "response": {
    "data": [
      {
        "id": 1,
        "amount": 500.00,
        "payment_date": "2024-01-15",
        "payment_method": "bank_transfer",
        "reference": "BON-2024-001",
        "notes": "Pagamento parziale",
        "created_at": "2024-01-15T00:00:00Z"
      }
    ]
  }
}
```

### 2.3 Gestione Promemoria

#### POST /api/invoices/{id}/send-reminder
Invia un promemoria di pagamento
```json
{
  "endpoint": "/api/invoices/{id}/send-reminder",
  "method": "POST",
  "body": {
    "send_via": "whatsapp|email|sms",
    "message": "Messaggio personalizzato opzionale",
    "include_pdf": true
  },
  "response": {
    "success": true,
    "message": "Promemoria inviato con successo",
    "sent_via": "whatsapp",
    "sent_at": "2024-01-15T10:30:00Z",
    "pdf_url": "https://example.com/invoices/123.pdf"
  }
}
```

#### POST /api/invoices/send-bulk-reminders
Invia promemoria multipli
```json
{
  "endpoint": "/api/invoices/send-bulk-reminders",
  "method": "POST",
  "body": {
    "invoice_ids": [1, 2, 3],
    "send_via": "whatsapp",
    "template": "overdue_reminder",
    "custom_message": "Messaggio personalizzato opzionale"
  },
  "response": {
    "sent_count": 3,
    "failed_count": 0,
    "results": [
      {
        "invoice_id": 1,
        "success": true,
        "message": "Promemoria inviato"
      }
    ]
  }
}
```

#### GET /api/invoices/overdue
Ottiene fatture scadute
```json
{
  "endpoint": "/api/invoices/overdue",
  "method": "GET",
  "query_params": {
    "days_overdue": 7,
    "include_tenant_info": true
  },
  "response": {
    "data": [
      {
        "id": 1,
        "invoice_number": "INV-2024-001",
        "days_overdue": 15,
        "tenant": {
          "id": 1,
          "name": "Mario Rossi",
          "phone": "+39 123 456 7890",
          "email": "mario.rossi@email.com"
        }
      }
    ]
  }
}
```

### 2.4 Generazione PDF

#### GET /api/invoices/{id}/pdf
Genera PDF della fattura per SendPulse
```json
{
  "endpoint": "/api/invoices/{id}/pdf",
  "method": "GET",
  "query_params": {
    "include_logo": "true|false",
    "include_qr_code": "true|false",
    "include_payment_instructions": "true|false"
  },
  "response": "application/pdf"
}
```

### 2.5 Statistiche e KPI

#### GET /api/invoices/statistics
Recupera statistiche delle fatture
```json
{
  "endpoint": "/api/invoices/statistics",
  "method": "GET",
  "query_params": {
    "period": "this_month|last_month|this_year|all"
  },
  "response": {
    "total_invoiced": 15000.00,
    "total_paid": 12000.00,
    "total_unpaid": 3000.00,
    "overdue_invoices": 5,
    "this_month_invoices": 25,
    "average_payment_time": 12.5,
    "payment_methods_distribution": {
      "bank_transfer": 60,
      "cash": 25,
      "credit_card": 10,
      "check": 5
    },
    "monthly_trends": [
      {
        "month": "2024-01",
        "invoiced": 5000.00,
        "paid": 4500.00
      }
    ]
  }
}
```

## 3. Integrazione SendPulse

### 3.1 Configurazione
```php
// config/sendpulse.php
return [
    'api_key' => env('SENDPULSE_API_KEY'),
    'api_secret' => env('SENDPULSE_API_SECRET'),
    'whatsapp_bot_id' => env('SENDPULSE_WHATSAPP_BOT_ID'),
    'default_phone' => env('SENDPULSE_DEFAULT_PHONE'),
];
```

### 3.2 Servizio SendPulse
```php
// app/Services/SendPulseService.php
class SendPulseService
{
    public function sendWhatsAppMessage($phone, $message, $pdfUrl = null)
    {
        $data = [
            'bot_id' => config('sendpulse.whatsapp_bot_id'),
            'phone' => $phone,
            'message' => $message
        ];
        
        if ($pdfUrl) {
            $data['attachments'] = [
                [
                    'type' => 'document',
                    'url' => $pdfUrl,
                    'filename' => 'fattura.pdf'
                ]
            ];
        }
        
        return $this->makeApiCall('/whatsapp/send', $data);
    }
    
    public function generateInvoiceMessage($invoice)
    {
        $tenant = $invoice->tenant;
        $apartment = $invoice->apartment;
        
        $message = "🏠 *FATTURA {$invoice->invoice_number}*\n\n";
        $message .= "📅 *Periodo:* " . $this->getPeriodLabel($invoice) . "\n";
        $message .= "👤 *Inquilino:* {$tenant->name}\n";
        $message .= "🏢 *Appartamento:* {$apartment->name}\n\n";
        
        $message .= "💰 *Dettaglio Spese:*\n";
        foreach ($invoice->items as $item) {
            $message .= "• {$item->description}: " . number_format($item->amount, 2, ',', '.') . "€\n";
        }
        
        $message .= "\n💶 *Totale da Pagare:* " . number_format($invoice->total, 2, ',', '.') . "€\n";
        $message .= "📅 *Scadenza:* " . $invoice->due_date->format('d/m/Y') . "\n\n";
        
        $message .= "💳 *Modalità di Pagamento:*\n";
        $message .= "• Bonifico Bancario\n";
        $message .= "• IBAN: IT60 X054 2811 1010 0000 0123 456\n";
        $message .= "• Causale: {$invoice->invoice_number}\n\n";
        
        $message .= "📞 Per informazioni: +39 123 456 7890\n";
        $message .= "📧 Email: info@agriturismo.it\n\n";
        
        $message .= "Grazie per la fiducia! 🙏";
        
        return $message;
    }
}
```

### 3.3 Controller per SendPulse
```php
// app/Http/Controllers/InvoiceController.php
public function sendReminder(Request $request, $id)
{
    $invoice = Invoice::with(['tenant', 'apartment', 'items'])->findOrFail($id);
    
    // Genera PDF
    $pdfPath = $this->generateInvoicePdf($invoice);
    $pdfUrl = Storage::url($pdfPath);
    
    // Genera messaggio WhatsApp
    $message = $this->sendPulseService->generateInvoiceMessage($invoice);
    
    // Invia via SendPulse
    $result = $this->sendPulseService->sendWhatsAppMessage(
        $invoice->tenant->phone,
        $message,
        $pdfUrl
    );
    
    if ($result['success']) {
        // Aggiorna stato promemoria
        $invoice->update([
            'reminder_sent' => true,
            'reminder_date' => now()
        ]);
        
        return response()->json([
            'success' => true,
            'message' => 'Promemoria inviato con successo',
            'sent_via' => 'whatsapp'
        ]);
    }
    
    return response()->json([
        'success' => false,
        'message' => 'Errore nell\'invio del promemoria'
    ], 500);
}
```

## 4. Validazioni

### 4.1 Request Validation
```php
// app/Http/Requests/InvoiceRequest.php
class InvoiceRequest extends FormRequest
{
    public function rules()
    {
        return [
            'tenant_id' => 'required|exists:tenants,id',
            'apartment_id' => 'required|exists:apartments,id',
            'month' => 'required|integer|between:1,12',
            'year' => 'required|integer|min:2020',
            'issue_date' => 'required|date',
            'due_date' => 'required|date|after:issue_date',
            'notes' => 'nullable|string|max:1000',
            'items' => 'required|array|min:1',
            'items.*.type' => 'required|in:rent,electricity,water,gas,maintenance,other',
            'items.*.description' => 'required|string|max:255',
            'items.*.amount' => 'required|numeric|min:0'
        ];
    }
}
```

## 5. Eventi e Notifiche

### 5.1 Eventi
```php
// app/Events/InvoiceCreated.php
class InvoiceCreated
{
    public $invoice;
    
    public function __construct(Invoice $invoice)
    {
        $this->invoice = $invoice;
    }
}

// app/Events/InvoicePaid.php
class InvoicePaid
{
    public $invoice;
    
    public function __construct(Invoice $invoice)
    {
        $this->invoice = $invoice;
    }
}

// app/Events/InvoiceOverdue.php
class InvoiceOverdue
{
    public $invoice;
    
    public function __construct(Invoice $invoice)
    {
        $this->invoice = $invoice;
    }
}
```

### 5.2 Listeners
```php
// app/Listeners/SendInvoiceNotification.php
class SendInvoiceNotification
{
    public function handle(InvoiceCreated $event)
    {
        // Invia notifica all'inquilino
        $event->invoice->tenant->notify(new InvoiceCreatedNotification($event->invoice));
    }
}

// app/Listeners/SendOverdueReminder.php
class SendOverdueReminder
{
    public function handle(InvoiceOverdue $event)
    {
        // Invia promemoria automatico
        $this->sendPulseService->sendWhatsAppMessage(
            $event->invoice->tenant->phone,
            $this->generateOverdueMessage($event->invoice)
        );
    }
}
```

## 6. Comandi Artisan

### 6.1 Generazione Fatture Automatiche
```php
// app/Console/Commands/GenerateMonthlyInvoices.php
class GenerateMonthlyInvoices extends Command
{
    protected $signature = 'invoices:generate-monthly';
    
    public function handle()
    {
        $activeLeases = Lease::where('status', 'active')->get();
        
        foreach ($activeLeases as $lease) {
            $this->generateInvoiceForLease($lease);
        }
        
        $this->info('Fatture mensili generate con successo');
    }
}
```

### 6.2 Invio Promemoria Automatici
```php
// app/Console/Commands/SendOverdueReminders.php
class SendOverdueReminders extends Command
{
    protected $signature = 'invoices:send-overdue-reminders';
    
    public function handle()
    {
        $overdueInvoices = Invoice::where('is_paid', false)
            ->where('due_date', '<', now())
            ->where('reminder_sent', false)
            ->get();
        
        foreach ($overdueInvoices as $invoice) {
            $this->sendReminder($invoice);
        }
    }
}
```

## 7. Configurazione Cron Jobs

```bash
# /etc/crontab
# Genera fatture mensili il primo del mese
0 9 1 * * www-data php /path/to/artisan invoices:generate-monthly

# Invia promemoria scaduti ogni giorno alle 10:00
0 10 * * * www-data php /path/to/artisan invoices:send-overdue-reminders
```

## 8. Variabili d'Ambiente

```env
# SendPulse Configuration
SENDPULSE_API_KEY=your_api_key
SENDPULSE_API_SECRET=your_api_secret
SENDPULSE_WHATSAPP_BOT_ID=your_bot_id
SENDPULSE_DEFAULT_PHONE=+39xxxxxxxxx

# Invoice Configuration
INVOICE_PREFIX=INV
INVOICE_START_NUMBER=1
DEFAULT_TAX_RATE=22.00
DEFAULT_DUE_DAYS=30
DEFAULT_PAYMENT_METHOD=bank_transfer

# Company Information
COMPANY_NAME="Agriturismo Manager"
COMPANY_ADDRESS="Via delle Rose, 123"
COMPANY_CITY="12345 Città, Italia"
COMPANY_PHONE="+39 123 456 7890"
COMPANY_EMAIL="info@agriturismo.it"
COMPANY_IBAN="IT60 X054 2811 1010 0000 0123 456"
COMPANY_VAT_NUMBER="12345678901"
COMPANY_LOGO_URL="https://example.com/logo.png"

# Utility Costs (per unità)
ELECTRICITY_COST_PER_KWH=0.25
WATER_COST_PER_M3=1.50
GAS_COST_PER_M3=0.80

# Notification Settings
DEFAULT_REMINDER_DAYS=7
OVERDUE_REMINDER_DAYS=3
AUTO_SEND_REMINDERS=true
WHATSAPP_NOTIFICATIONS_ENABLED=true
EMAIL_NOTIFICATIONS_ENABLED=true

# PDF Generation
PDF_STORAGE_PATH=/storage/invoices
PDF_TEMPLATE_PATH=/resources/templates/invoice
INCLUDE_QR_CODE=true
INCLUDE_PAYMENT_INSTRUCTIONS=true

# Database Configuration
INVOICE_NUMBER_SEQUENCE=invoice_sequence
MAX_INVOICE_NUMBER_LENGTH=10
```

## 9. Test

### 9.1 Unit Tests
```php
// tests/Unit/InvoiceTest.php
class InvoiceTest extends TestCase
{
    public function test_can_create_invoice()
    {
        $invoiceData = [
            'tenant_id' => 1,
            'apartment_id' => 1,
            'month' => 1,
            'year' => 2024,
            'items' => [
                ['type' => 'rent', 'description' => 'Affitto', 'amount' => 800]
            ]
        ];
        
        $response = $this->postJson('/api/invoices', $invoiceData);
        
        $response->assertStatus(201)
                ->assertJsonStructure(['id', 'invoice_number']);
    }
}
```

### 9.2 Feature Tests
```php
// tests/Feature/InvoiceManagementTest.php
class InvoiceManagementTest extends TestCase
{
    public function test_can_send_reminder()
    {
        $invoice = Invoice::factory()->create();
        
        $response = $this->postJson("/api/invoices/{$invoice->id}/send-reminder");
        
        $response->assertStatus(200)
                ->assertJson(['success' => true]);
    }
}
```

## 10. Sicurezza

### 10.1 Middleware
```php
// app/Http/Middleware/InvoiceAccess.php
class InvoiceAccess
{
    public function handle($request, Closure $next)
    {
        $invoice = $request->route('invoice');
        
        if (!$this->canAccessInvoice($request->user(), $invoice)) {
            abort(403, 'Accesso negato');
        }
        
        return $next($request);
    }
}
```

### 10.2 Policies
```php
// app/Policies/InvoicePolicy.php
class InvoicePolicy
{
    public function view(User $user, Invoice $invoice)
    {
        return $user->role === 'admin' || 
               $user->id === $invoice->tenant->user_id;
    }
    
    public function create(User $user)
    {
        return in_array($user->role, ['admin', 'manager']);
    }
}
```

## 11. Performance e Ottimizzazione

### 11.1 Indici Database
```sql
-- Indici per ottimizzare le query
CREATE INDEX idx_invoices_composite ON invoices(tenant_id, apartment_id, month, year);
CREATE INDEX idx_invoices_status_date ON invoices(is_paid, due_date);
CREATE INDEX idx_invoices_reminder ON invoices(reminder_sent, due_date);
```

### 11.2 Caching
```php
// Cache delle statistiche
Cache::remember('invoice_statistics', 3600, function () {
    return Invoice::selectRaw('
        COUNT(*) as total,
        SUM(CASE WHEN is_paid = 1 THEN 1 ELSE 0 END) as paid,
        SUM(CASE WHEN is_paid = 0 AND due_date < CURDATE() THEN 1 ELSE 0 END) as overdue,
        SUM(total) as total_amount,
        SUM(CASE WHEN is_paid = 1 THEN total ELSE 0 END) as paid_amount
    ')->first();
});
```

## 12. Monitoraggio e Logging

### 12.1 Logging
```php
// Log delle operazioni importanti
Log::info('Invoice created', [
    'invoice_id' => $invoice->id,
    'tenant_id' => $invoice->tenant_id,
    'amount' => $invoice->total
]);

Log::warning('Invoice overdue', [
    'invoice_id' => $invoice->id,
    'days_overdue' => $invoice->due_date->diffInDays(now())
]);
```

### 12.2 Metriche
```php
// Metriche per monitoring
Metrics::counter('invoices_created')->increment();
Metrics::gauge('total_unpaid_amount')->set($totalUnpaid);
Metrics::histogram('payment_time')->observe($paymentTime);
```

## 13. Deployment Checklist

### Database Setup
- [ ] Eseguire migrazioni database per tabelle invoices, invoice_items, payment_records
- [ ] Creare indici per ottimizzare le performance
- [ ] Configurare sequenza per numeri fattura
- [ ] Verificare foreign key constraints

### Configurazione Ambiente
- [ ] Configurare tutte le variabili d'ambiente
- [ ] Installare dipendenze SendPulse
- [ ] Configurare storage per PDF
- [ ] Verificare permessi file storage
- [ ] Configurare template PDF

### Integrazione Frontend
- [ ] Verificare compatibilità con GenericApiService
- [ ] Testare endpoint CRUD standard
- [ ] Testare endpoint specifici per fatturazione
- [ ] Verificare integrazione con tenant, apartment, lease, utility
- [ ] Testare generazione automatica fatture
- [ ] Verificare gestione errori senza fallback mock
- [ ] Testare componenti con dati vuoti
- [ ] Verificare messaggi di errore appropriati
- [ ] Testare cache invalidation

### Notifiche e SendPulse
- [ ] Configurare account SendPulse
- [ ] Testare invio messaggi WhatsApp
- [ ] Testare invio PDF via SendPulse
- [ ] Configurare template messaggi
- [ ] Testare promemoria automatici

### Automazione
- [ ] Configurare cron jobs per generazione mensile
- [ ] Configurare cron jobs per promemoria scaduti
- [ ] Testare comandi Artisan
- [ ] Configurare backup automatici

### Monitoring e Sicurezza
- [ ] Configurare logging per operazioni fatturazione
- [ ] Configurare monitoring performance
- [ ] Testare gestione errori
- [ ] Verificare autorizzazioni e policy
- [ ] Configurare audit trail

### Testing Completo
- [ ] Test unitari per tutti i servizi
- [ ] Test integrazione API
- [ ] Test generazione PDF
- [ ] Test invio notifiche
- [ ] Test scenario di errore
- [ ] Test performance con dati reali

## 14. Documentazione API

Generare documentazione completa con Swagger/OpenAPI per tutti gli endpoint.

## 15. Integrazione Frontend Angular

### 15.1 Aggiornamento InvoiceService
Il `InvoiceService` è stato completamente aggiornato per utilizzare solo dati reali dal database:

```typescript
// Tutti i metodi utilizzano solo dati reali dal database
getAllInvoices(params?: any): Observable<Invoice[]> {
  return this.apiService.getAll<Invoice>('invoices', params).pipe(
    catchError(error => {
      console.error('Errore nel recupero delle fatture:', error);
      return throwError(() => new Error('Impossibile recuperare le fatture dal database'));
    })
  );
}

getInvoiceById(id: number): Observable<Invoice> {
  return this.apiService.getById<Invoice>('invoices', id).pipe(
    catchError(error => {
      console.error(`Errore nel recupero della fattura ${id}:`, error);
      return throwError(() => new Error(`Fattura con ID ${id} non trovata`));
    })
  );
}

createInvoice(invoice: Partial<Invoice>): Observable<Invoice> {
  return this.apiService.create<Invoice>('invoices', invoice).pipe(
    tap(() => this.apiService.invalidateCache('invoices')),
    catchError(error => {
      console.error('Errore nella creazione della fattura:', error);
      return throwError(() => new Error('Impossibile creare la fattura'));
    })
  );
}

updateInvoice(id: number, invoice: Partial<Invoice>): Observable<Invoice> {
  return this.apiService.update<Invoice>('invoices', id, invoice).pipe(
    tap(() => this.apiService.invalidateCache('invoices', id)),
    catchError(error => {
      console.error(`Errore nell'aggiornamento della fattura ${id}:`, error);
      return throwError(() => new Error(`Impossibile aggiornare la fattura ${id}`));
    })
  );
}

deleteInvoice(id: number): Observable<void> {
  return this.apiService.delete('invoices', id).pipe(
    tap(() => this.apiService.invalidateCache('invoices', id)),
    catchError(error => {
      console.error(`Errore nell'eliminazione della fattura ${id}:`, error);
      return throwError(() => new Error(`Impossibile eliminare la fattura ${id}`));
    })
  );
}
```

### 15.2 Metodi Specifici per Fatturazione
```typescript
// Metodi per funzionalità specifiche
markAsPaid(invoiceId: number, paymentData: any): Observable<Invoice> {
  return this.http.post<Invoice>(`${this.apiUrl}/${invoiceId}/mark-as-paid`, paymentData);
}

sendReminder(invoiceId: number, reminderData: any): Observable<any> {
  return this.http.post<any>(`${this.apiUrl}/${invoiceId}/send-reminder`, reminderData);
}

generatePdf(invoiceId: number): Observable<Blob> {
  return this.http.get(`${this.apiUrl}/${invoiceId}/pdf`, { responseType: 'blob' });
}

generateMonthlyInvoices(data: any): Observable<any> {
  return this.http.post<any>(`${this.apiUrl}/generate-monthly`, data);
}
```

### 15.3 Integrazione con Entità Esistenti
```typescript
// Utilizzare i metodi esistenti del GenericApiService
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
```

### 15.4 Gestione Errori Senza Fallback
Il sistema ora gestisce gli errori senza fallback ai dati mock:

```typescript
// Gestione errori con throwError invece di fallback
catchError(error => {
  console.error('Errore specifico:', error);
  return throwError(() => new Error('Messaggio di errore specifico'));
})
```

**Vantaggi di questa approccio:**
- **Dati sempre coerenti**: Nessun rischio di mostrare dati obsoleti o inconsistenti
- **Gestione errori trasparente**: Gli errori vengono propagati ai componenti per gestione UI appropriata
- **Debugging migliorato**: Gli errori sono sempre visibili e tracciabili
- **Performance ottimale**: Nessun overhead per gestione dati mock
- **UX migliore**: I componenti possono mostrare messaggi appropriati quando non ci sono dati

**Gestione UI degli errori:**
```typescript
// Nei componenti, gestire gli errori per mostrare messaggi appropriati
this.invoiceService.getAllInvoices().pipe(
  catchError(error => {
    this.showErrorMessage('Nessuna fattura disponibile');
    return of([]); // Array vuoto per evitare errori nel template
  })
).subscribe(invoices => {
  this.invoices = invoices;
});
```

## 16. Riepilogo Modifiche Completate

### ✅ Rimozione Completa Dati Mock
- **Eliminati tutti i fallback ai dati mock** dal `InvoiceService`
- **Rimossi array mock**: `mockInvoices`, `mockInvoiceItems`, `mockPaymentRecords`
- **Sostituiti con throwError**: Tutti i metodi ora propagano errori reali
- **Gestione errori trasparente**: Gli errori vengono gestiti dai componenti UI

### ✅ Integrazione Completa con API Reali
- **CRUD Operations**: Tutti i metodi utilizzano `GenericApiService`
- **Cache Management**: Invalidazione automatica della cache
- **Error Handling**: Gestione errori con messaggi specifici
- **Type Safety**: Mantenuta la type safety TypeScript

### ✅ Funzionalità Avanzate
- **Generazione Automatica**: Fatture mensili e da contratto
- **Gestione Pagamenti**: Record di pagamento integrati
- **Promemoria**: Invio via SendPulse WhatsApp
- **Statistiche**: KPI e metriche fatturazione
- **PDF Generation**: Generazione documenti per invio

### ✅ Integrazione Entità Esistenti
- **Tenant**: Filtri per tenant attivi con contratti
- **Apartment**: Filtri per appartamenti occupati
- **Lease**: Generazione fatture da contratti attivi
- **Utility**: Calcolo costi da letture utility

## 17. Supporto e Manutenzione

- Monitoraggio continuo delle performance
- Backup automatici del database
- Aggiornamenti di sicurezza
- Supporto tecnico per integrazione SendPulse
- Training per il personale
- Monitoraggio integrazione frontend-backend
- Aggiornamenti API e documentazione
- **Gestione errori senza fallback**: Monitoraggio errori reali
- **Performance monitoring**: Ottimizzazione query database
- **Cache optimization**: Monitoraggio efficienza cache 