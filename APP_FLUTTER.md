# Agriturismo Backend — Documentazione completa + Specifica App Flutter iOS

Questo documento è auto-contenuto, pronto al copy‑paste in Cursor AI, con esempi di codice completi e istruzioni passo‑passo per integrare le API backend esistenti e creare un’app Flutter iOS minimale e moderna.

────────────────────────────────────────────────────────────────────────────

SEZIONE 1 — DOCUMENTAZIONE BACKEND

1. Architettura e tecnologie
- Framework: FastAPI con Pydantic per validazione e serializzazione
- DB e ORM: SQLAlchemy (migrations con Alembic)
- Auth: JWT access token + refresh token, OAuth2PasswordBearer su /api/auth/login
- Sicurezza e robustezza: CORS configurato, rate limiting con slowapi, headers di sicurezza, cache HTTP in‑memory per GET non autenticati
- Static: cartelle static/ per immagini/documenti
- Routers registrati: /apartments, /tenants, /leases, /utilities, /invoices, /api/auth, /users, /settings

Base URL
- Imposta nel client: BASE_URL = "https://flat-damselfly-agriturismo-backend-47075869.koyeb.app/"

2. Autenticazione
Endpoint prefix: /api/auth
- POST /api/auth/login
  Input: OAuth2PasswordRequestForm (username, password)
  Output: { accessToken, refreshToken, tokenType:"bearer", expiresIn }
- POST /api/auth/refresh-token
  Body: { "refresh_token": "..." }
  Output: TokenPair
- POST /api/auth/logout
  Body: { "refresh_token": "..." }
  Output: 200 OK
- POST /api/auth/logout-all (revoca tutti i refresh token dell’utente)
- PUT /api/auth/change-password
- GET /api/auth/verify-token
- GET /api/auth/csrf-token
- POST /api/auth/forgot-password
- POST /api/auth/reset-password

Note
- Inserisci sempre Authorization: Bearer <accessToken> dove richiesto.
- refreshToken va conservato in storage sicuro e usato per ottenere un nuovo accessToken.

3. API principali per App Flutter (utenze e appartamenti)
Prefix utilities: /utilities
- GET /utilities
  Lista letture, con filtri: apartmentId, type, subtype, year, month, isPaid
- GET /utilities/types
  Config tipi utility: electricity, water, gas con label/unit/costo default
- GET /utilities/{reading_id}
- POST /utilities
  Crea nuova lettura mensile con calcolo consumo/costo lato server
- PUT /utilities/{reading_id}
- DELETE /utilities/{reading_id}
- PATCH /utilities/{reading_id}/mark-paid
- GET /utilities/apartment/{apartmentId}
- GET /utilities/apartment/{apartmentId}/last/{type}
- GET /utilities/summary/{apartmentId}
- GET /utilities/statistics/{year}
- GET /utilities/apartment/{apartmentId}/consumption/{year}
- GET /utilities/unpaid/list
- GET /utilities/statistics/overview
- GET /utilities/last-reading/{apartmentId}/{type}?subtype=...
  Per auto‑compilazione form: ultima lettura e data
- POST /utilities/bulk

Prefix apartments: /apartments
- GET /apartments
- GET /apartments/{apartmentId}
- POST /apartments
- PUT /apartments/{apartmentId}
- PATCH /apartments/{apartmentId}/status
- GET /apartments/{apartmentId}/utilities
- … (tenants, leases, invoices disponibili; per l’app Flutter minimal servono apartments/utilities + auth)

Prefix invoices: /invoices (protetti, richiedono utente attivo)

4. Modelli dati (estratto, JSON esemplificativi)
UtilityReadingCreate (request)
{
  "apartmentId": 25,
  "type": "electricity",        // electricity | water | gas
  "readingDate": "2025-10-01",
  "previousReading": 1234.5,
  "currentReading": 1278.0,
  "consumption": 43.5,          // calcolato lato server se non presente
  "unitCost": 0.22,
  "totalCost": 9.57,            // consumption * unitCost
  "isPaid": false,
  "notes": "",
  "subtype": null,
  "isSpecialReading": false
}

UtilityReading (response)
{
  "id": 101,
  "apartmentId": 25,
  "type": "electricity",
  "readingDate": "2025-10-01",
  "previousReading": 1234.5,
  "currentReading": 1278.0,
  "consumption": 43.5,
  "unitCost": 0.22,
  "totalCost": 9.57,
  "isPaid": false,
  "notes": null,
  "subtype": null,
  "isSpecialReading": false,
  "paidDate": null,
  "createdAt": "2025-10-01T10:00:00Z",
  "updatedAt": "2025-10-01T10:00:00Z"
}

LastReading (per auto‑compilazione)
{
  "apartmentId": 25,
  "type": "electricity",
  "lastReading": 1234.5,
  "lastReadingDate": "2025-09-01",
  "hasHistory": true,
  "subtype": null
}

Apartment (estratto)
{
  "id": 25,
  "name": "Appartamento A",
  "floor": 1,
  "squareMeters": 45,
  "rooms": 2,
  "bathrooms": 1,
  "monthlyRent": 650,
  "status": "available",
  "images": [],
  "createdAt": "2025-01-01T00:00:00Z",
  "updatedAt": "2025-10-01T00:00:00Z"
}

5. Flusso operativo — Inserimento letture mensili
- Step 1: Seleziona appartamento (lista rapida) → ottieni id
- Step 2: Recupera ultima lettura: GET /utilities/last-reading/{apartmentId}/{type}
- Step 3: Precompila previousReading e unità/costo da /utilities/types
- Step 4: Inserisci currentReading, valida in tempo reale (current ≥ previous)
- Step 5: Calcola consumption e totalCost lato client per feedback, comunque ricalcolati lato server
- Step 6: Invia POST /utilities con payload completo
- Step 7: Mostra conferma e aggiorna ultimo valore

Status e errori comuni
- 400: currentReading < lastReading (messaggio esplicito)
- 404: Apartment/Reading not found
- 401: token mancante/invalidato su endpoint protetti
- Rate limiting: su login/registrazione

6. Best practices integrazione client
- Autenticazione: mantieni accessToken in memoria sicura; refresh con refreshToken
- Errori: gestisci 4xx/5xx con messaggi chiari; riprova su network error
- Sicurezza: Authorization Bearer; usa HTTPS; no caching client per API
- Performance: usa GET specifici (last-reading) per compilazione rapida; paginazione (skip/limit)

────────────────────────────────────────────────────────────────────────────

SEZIONE 2 — SPECIFICA APP FLUTTER iOS

Obiettivo UX
- Interfaccia minimal e moderna
- Un tap per selezionare appartamento, un tap per inserire lettura
- Form unico per tutte le utenze per appartamento
- Validazione in tempo reale e feedback immediato

Palette colori (professionale)
- Primary: #1E88E5 (blu)
- Accent: #43A047 (verde)
- Warning: #FB8C00 (arancio)
- Background: #F5F7FA

State management consigliato: Riverpod
- Semplice, testabile, performante

Dipendenze Flutter suggerite (pubspec.yaml)
- flutter_riverpod: ^2.5.1
- http: ^1.2.0
- intl: ^0.19.0

Struttura minima file (esempi copy‑paste)

main.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'src/app.dart';

void main() {
  runApp(const ProviderScope(child: MyApp()));
}

src/app.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'theme.dart';
import 'pages/login_page.dart';

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Agriturismo',
      theme: buildTheme(),
      home: const LoginPage(),
    );
  }
}

src/theme.dart
import 'package:flutter/material.dart';
ThemeData buildTheme() {
  const primary = Color(0xFF1E88E5);
  const accent = Color(0xFF43A047);
  const bg = Color(0xFFF5F7FA);
  return ThemeData(
    colorScheme: const ColorScheme.light(primary: primary, secondary: accent),
    scaffoldBackgroundColor: bg,
    inputDecorationTheme: const InputDecorationTheme(
      border: OutlineInputBorder(),
    ),
    useMaterial3: true,
  );
}

src/core/api_client.dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiClient {
  final String baseUrl;
  String? _accessToken;
  ApiClient(this.baseUrl);

  void setAccessToken(String? token) { _accessToken = token; }

  Map<String,String> _headers({bool json=true}) => {
    if (json) 'Content-Type':'application/json',
    if (_accessToken!=null) 'Authorization':'Bearer ${_accessToken!}',
  };

  Future<Map<String,dynamic>> login(String username, String password) async {
    final url = Uri.parse('$baseUrl/api/auth/login');
    final res = await http.post(url, headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:{
      'username': username, 'password': password
    });
    if (res.statusCode==200) return jsonDecode(res.body);
    throw Exception('Login failed: ${res.statusCode} ${res.body}');
  }

  Future<List<dynamic>> getApartments() async {
    final url = Uri.parse('$baseUrl/apartments');
    final res = await http.get(url, headers:_headers());
    if (res.statusCode==200) return jsonDecode(res.body);
    throw Exception('Get apartments failed: ${res.statusCode}');
  }

  Future<List<dynamic>> getUtilityTypes() async {
    final url = Uri.parse('$baseUrl/utilities/types');
    final res = await http.get(url, headers:_headers());
    if (res.statusCode==200) return jsonDecode(res.body);
    throw Exception('Get types failed: ${res.statusCode}');
  }

  Future<Map<String,dynamic>> getLastReading(int apartmentId, String type, {String? subtype}) async {
    final url = Uri.parse('$baseUrl/utilities/last-reading/$apartmentId/$type${subtype!=null?'?subtype=$subtype':''}');
    final res = await http.get(url, headers:_headers());
    if (res.statusCode==200) return jsonDecode(res.body);
    if (res.statusCode==404) return {'hasHistory':false,'lastReading':0,'lastReadingDate':null,'apartmentId':apartmentId,'type':type};
    throw Exception('Get last reading failed: ${res.statusCode}');
  }

  Future<Map<String,dynamic>> createReading(Map<String,dynamic> payload) async {
    final url = Uri.parse('$baseUrl/utilities');
    final res = await http.post(url, headers:_headers(), body: jsonEncode(payload));
    if (res.statusCode==201 || res.statusCode==200) return jsonDecode(res.body);
    throw Exception('Create reading failed: ${res.statusCode} ${res.body}');
  }
}

src/core/providers.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'api_client.dart';

const BASE_URL = 'https://flat-damselfly-agriturismo-backend-47075869.koyeb.app/';
final apiClientProvider = Provider<ApiClient>((ref)=>ApiClient(BASE_URL));

class AuthState { final String? accessToken; const AuthState(this.accessToken); }
class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier(this._client): super(const AuthState(null));
  final ApiClient _client;
  Future<void> login(String u, String p) async {
    final data = await _client.login(u,p);
    _client.setAccessToken(data['accessToken']);
    state = AuthState(data['accessToken']);
  }
}
final authProvider = StateNotifierProvider<AuthNotifier,AuthState>((ref){
  final client = ref.read(apiClientProvider);
  return AuthNotifier(client);
});

final apartmentsProvider = FutureProvider<List<Map<String,dynamic>>>((ref) async {
  final client = ref.read(apiClientProvider);
  final list = await client.getApartments();
  return List<Map<String,dynamic>>.from(list);
});

final utilityTypesProvider = FutureProvider<List<Map<String,dynamic>>>((ref) async {
  final client = ref.read(apiClientProvider);
  final list = await client.getUtilityTypes();
  return List<Map<String,dynamic>>.from(list);
});

final selectedApartmentIdProvider = StateProvider<int?>((ref)=>null);
final selectedTypeProvider = StateProvider<String>((ref)=>'electricity');
final selectedSubtypeProvider = StateProvider<String?>((ref)=>null);

final lastReadingProvider = FutureProvider<Map<String,dynamic>>((ref) async {
  final client = ref.read(apiClientProvider);
  final aptId = ref.watch(selectedApartmentIdProvider);
  final type = ref.watch(selectedTypeProvider);
  final subtype = ref.watch(selectedSubtypeProvider);
  if (aptId==null) return {'hasHistory':false,'lastReading':0};
  return await client.getLastReading(aptId, type, subtype: subtype);
});

src/pages/login_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/providers.dart';
import 'select_apartment_page.dart';

class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key});
  @override ConsumerState<LoginPage> createState()=>_LoginPageState();
}
class _LoginPageState extends ConsumerState<LoginPage>{
  final _u = TextEditingController();
  final _p = TextEditingController();
  bool _loading=false; String? _error;
  @override Widget build(BuildContext ctx){
    return Scaffold(
      appBar: AppBar(title: const Text('Accedi')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(children:[
          TextField(controller:_u, decoration: const InputDecoration(labelText:'Username')),
          const SizedBox(height:8),
          TextField(controller:_p, decoration: const InputDecoration(labelText:'Password'), obscureText:true),
          const SizedBox(height:16),
          if (_error!=null) Text(_error!, style: const TextStyle(color: Colors.red)),
          ElevatedButton(onPressed:_loading?null:() async {
            setState(()=>_loading=true);
            try{
              await ref.read(authProvider.notifier).login(_u.text.trim(), _p.text);
              if (ctx.mounted) Navigator.pushReplacement(ctx, MaterialPageRoute(builder:(_)=>const SelectApartmentPage()));
            }catch(e){ setState(()=>_error=e.toString()); }
            setState(()=>_loading=false);
          }, child: Text(_loading? '...' : 'Entra'))
        ]),
      ),
    );
  }
}

src/pages/select_apartment_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/providers.dart';
import 'add_reading_page.dart';

class SelectApartmentPage extends ConsumerWidget {
  const SelectApartmentPage({super.key});
  @override Widget build(BuildContext ctx, WidgetRef ref){
    final apartments = ref.watch(apartmentsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Seleziona appartamento')),
      body: apartments.when(
        data:(list){
          return ListView.separated(
            itemCount: list.length,
            separatorBuilder: (_, __)=>const Divider(height:1),
            itemBuilder: (_,i){
              final a = list[i];
              return ListTile(
                title: Text(a['name']??'Appartamento ${a['id']}'),
                subtitle: Text('Piano ${a['floor']} • ${a['squareMeters']} m²'),
                onTap:(){
                  ref.read(selectedApartmentIdProvider.notifier).state = a['id'] as int;
                  Navigator.push(ctx, MaterialPageRoute(builder:(_)=>const AddReadingPage()));
                }
              );
            },
          );
        },
        loading:()=>const Center(child:CircularProgressIndicator()),
        error:(e,_)=>Center(child:Text('Errore: $e')),
      ),
    );
  }
}

src/pages/add_reading_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/providers.dart';
import 'package:intl/intl.dart';

class AddReadingPage extends ConsumerStatefulWidget {
  const AddReadingPage({super.key});
  @override ConsumerState<AddReadingPage> createState()=>_AddReadingPageState();
}
class _AddReadingPageState extends ConsumerState<AddReadingPage>{
  final _current = TextEditingController();
  final _unitCost = TextEditingController(text:'0.22');
  String _type = 'electricity';
  String? _subtype;
  String? _error; bool _loading=false; double _cons=0; double _total=0;

  @override void initState(){ super.initState(); ref.read(selectedTypeProvider.notifier).state=_type; ref.read(selectedSubtypeProvider.notifier).state=null; }

  @override Widget build(BuildContext ctx){
    final last = ref.watch(lastReadingProvider);
    final aptId = ref.watch(selectedApartmentIdProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Inserisci lettura')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(children:[
          // selettore semplice per tipo
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value:'electricity',label:Text('Luce')),
              ButtonSegment(value:'water',label:Text('Acqua')),
              ButtonSegment(value:'gas',label:Text('Gas')),
            ],
            selected: {_type},
            onSelectionChanged:(s){ setState(()=>_type=s.first); ref.read(selectedTypeProvider.notifier).state=_type; },
          ),
          const SizedBox(height:12),
          if (aptId==8 && _type=='electricity') SegmentedButton<String>(
            segments: const [
              ButtonSegment(value:'main',label:Text('Principale')),
              ButtonSegment(value:'laundry',label:Text('Lavanderia')),
            ],
            selected: {_subtype ?? 'main'},
            onSelectionChanged:(s){ setState(()=>_subtype=s.first); ref.read(selectedSubtypeProvider.notifier).state=_subtype; },
          ),
          last.when(
            data:(lr){
              final prev = (lr['lastReading']??0).toDouble();
              return Column(crossAxisAlignment: CrossAxisAlignment.start, children:[
                Text('Ultima lettura: ${prev.toStringAsFixed(2)}'),
                const SizedBox(height:8),
                TextField(controller:_current, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText:'Lettura attuale'),
                  onChanged:(v){
                    final cur = double.tryParse(v)??0;
                    final u = double.tryParse(_unitCost.text)??0;
                    setState(()=>_cons = (cur - prev).clamp(0,double.infinity));
                    setState(()=>_total = _cons * u);
                    _error = cur < prev ? 'La lettura attuale deve essere ≥ ultima' : null;
                  },
                ),
                const SizedBox(height:8),
                TextField(controller:_unitCost, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText:'Costo unitario')), 
                const SizedBox(height:8),
                Text('Consumo: ${_cons.toStringAsFixed(2)} • Totale: € ${_total.toStringAsFixed(2)}'),
                if (_error!=null) Text(_error!, style: const TextStyle(color:Colors.red)),
                const SizedBox(height:12),
                ElevatedButton(onPressed:_loading||aptId==null?null:() async {
                  final cur = double.tryParse(_current.text)??0;
                  final prev = lr['lastReading']!=null? (lr['lastReading'] as num).toDouble() : 0;
                  if (cur < prev){ setState(()=>_error='La lettura attuale deve essere ≥ ultima'); return; }
                  setState(()=>_loading=true);
                  try{
                    final today = DateFormat('yyyy-MM-dd').format(DateTime.now());
                    final payload = {
                      'apartmentId': aptId,
                      'type': _type,
                      'readingDate': today,
                      'previousReading': prev,
                      'currentReading': cur,
                      'consumption': cur-prev,
                      'unitCost': double.tryParse(_unitCost.text)??0,
                      'totalCost': (cur-prev) * (double.tryParse(_unitCost.text)??0),
                      'isPaid': false,
                      'notes': null,
                      'subtype': _subtype,
                      'isSpecialReading': false,
                    };
                    final created = await ref.read(apiClientProvider).createReading(payload);
                    if (ctx.mounted) showDialog(context:ctx, builder:(_)=>AlertDialog(title: const Text('OK'), content: Text('Lettura salvata (id ${created['id']})'), actions:[TextButton(onPressed:(){Navigator.pop(ctx);}, child: const Text('Chiudi'))]));
                  }catch(e){ setState(()=>_error=e.toString()); }
                  setState(()=>_loading=false);
                }, child: Text(_loading? '...' : 'Salva'))
              ]);
            },
            loading:()=>const Center(child:CircularProgressIndicator()),
            error:(e,_)=>Text('Errore: $e'),
          ),
        ]),
      ),
    );
  }
}

Note UX
- Niente dropdown complessi: lista tap‑to‑select + segmented control per tipo
- Feedback immediato su consumo/totale e validazione
- Solo 2 passaggi: selezione → inserimento

Lavanderia (Appartamento 8 — ID 8)
- Mostra selettore sottotipo (SegmentedButton) solo se appartamento selezionato == 8 e tipo == electricity
- Sottotipi disponibili: main, laundry
- Chiamate API:
  - Ultima lettura lavanderia: GET /utilities/last-reading/8/electricity?subtype=laundry
  - Creazione lettura lavanderia: POST /utilities con 'subtype': 'laundry'
- Riverpod:
  - selectedSubtypeProvider: StateProvider<String?>
  - lastReadingProvider: passa subtype a getLastReading(...)
  - payload createReading: includi 'subtype' selezionato
- Regole di validazione: identiche (current ≥ previous)
- Reporting: electricity_laundry aggregato separatamente nel backend


Integrazione API (senza modifiche backend)
- Endpoints usati: /api/auth/login, /apartments, /utilities/last-reading/{apartmentId}/{type}, /utilities, /utilities/types
- Tutti già esistenti, nessuna modifica lato server

Deploy con Codemagic (senza Xcode)
1) Crea repository Flutter (GitHub/GitLab) con la struttura sopra
2) Su Codemagic: crea nuovo workflow Flutter
   - Seleziona canale stable e versione Flutter
   - iOS: abilita build .ipa senza code signing (unsigned IPA)
   - Configura script post‑build per esportare l’IPA nella sezione Artifacts
3) Avvia build → scarica .ipa dagli Artifacts

Installazione con AltStore (metodo gratuito 7 giorni)
1) Installa AltServer su Mac/Windows e collega iPhone via USB/Wi‑Fi
2) Installa AltStore su iPhone dal menu di AltServer
3) In AltStore (iPhone) → My Apps → + → seleziona il tuo .ipa
4) AltStore firma con Apple ID gratuito (valido 7 giorni) e installa l’app

Rinnovo automatico certificati
- AltStore tenta auto‑refresh ogni 7 giorni se AltServer è attivo sulla stessa rete
- Mantieni il dispositivo e AltServer raggiungibili periodicamente

Testing e debugging su dispositivo reale
- Inserisci un toggle “Debug” nell’app (es. mostra response/error in dialog/snackbar)
- Usa logging lato client (print/Logger) e codifica messaggi chiari dagli errori HTTP
- Per tracing back‑end, verifica i log su Koyeb e su FastAPI (main.py)

Checklist qualità
- Validazione locali: current ≥ previous, numeri ≥ 0
- Gestione 404 su last‑reading (nessuna storia → previous=0)
- Gestione errori 400 su POST utilities con messaggio dal server
- Aggiornamento stato e UI dopo creazione lettura
- HTTPS obbligatorio, BASE_URL corretto, token presente dove richiesto

Istruzioni specifiche — Lavanderia (Appartamento 8)

Contesto backend
- L’appartamento 8 ha una gestione speciale dell’elettricità per la lavanderia. Nel backend è mappato come apartment_id = 11 e le letture di lavanderia sono tracciate con subtype:"laundry" distinto dal principale ("main"). I costi della lavanderia vengono aggregati separatamente come electricity_laundry nelle statistiche/summary.

Come usare le API
- Ultima lettura lavanderia: GET /utilities/last-reading/8/electricity?subtype=laundry
- Creazione lettura lavanderia: POST /utilities con payload che include subtype:"laundry"
- Tipi e sottotipi: type="electricity" e subtype in {"main","laundry"} per l’appartamento 8 (ID 8). Per gli altri appartamenti, subtype può essere null.

Esempio payload creazione lettura lavanderia
{
  "apartmentId": 8,
  "type": "electricity",
  "subtype": "laundry",
  "readingDate": "2025-10-01",
  "previousReading": 500.0,
  "currentReading": 520.0,
  "consumption": 20.0,
  "unitCost": 0.22,
  "totalCost": 4.40,
  "isPaid": false,
  "notes": "Lavatrice mensile"
}

Aggiornamenti UI/UX (Flutter)
- Mostra un secondo selettore (SegmentedButton) per il sottotipo quando:
  - appartamento selezionato == 11 e tipo == electricity
  - segmenti: [main, laundry]
- Quando la selezione è "lavanderia", invia subtype:"laundry" in tutte le chiamate:
  - GET last-reading con query ?subtype=laundry
  - POST utilities con field subtype:"laundry"
- Quando la selezione è "principale", usa subtype:"main"; per appartamenti diversi da 11, puoi nascondere il selettore e inviare subtype=null.

Modifiche suggerite nei providers (Riverpod)
- Aggiungi un provider per il sottotipo e passa il valore alle chiamate:
  - selectedSubtypeProvider: StateProvider<String?> inizialmente null
  - lastReadingProvider: include subtype = ref.watch(selectedSubtypeProvider) e lo passa a getLastReading(..., subtype: subtype)
- In AddReadingPage, se aptId==11 e _type=='electricity', mostra il selettore sottotipo e aggiorna selectedSubtypeProvider.
- Nel payload di createReading, inserisci 'subtype': selectedSubtype (oppure null se non applicabile).

Note operative
- Validazione: mantieni le stesse regole (current ≥ previous) anche per la lavanderia.
- Reporting: i costi lavanderia saranno conteggiati separatamente nei summary/statistiche (chiave electricity_laundry).
- UX: mantieni il flusso a due passaggi; il selettore sottotipo compare solo quando serve, altrimenti la UI resta minimale.

Fine documento — pronto all’uso.