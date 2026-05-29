# Prompt ultra-dettagliato per coding agent — Home Assistant custom integration per Dreame MF10

## Contesto

Devi implementare una custom integration per Home Assistant per il ventilatore **Dreame Bladeless Fan MF10**.

Il dispositivo dell’utente ha questi dati:

```text
Model ID: dreame.fan.u2519
Device: Dreame Bladeless Fan MF10
MAC: 90:EB:48:22:90:EF
DID: -115387050
UID: BY603495
Firmware version: 1035
Plugin version: 104
```

Attualmente non esiste una integrazione Home Assistant ufficiale, HACS o add-on noto che supporti direttamente questo modello.

L’obiettivo è costruire una custom integration Home Assistant funzionante, idealmente partendo da codice esistente per dispositivi Dreame non-vacuum, in particolare integrazioni cloud-based tipo:

```text
https://github.com/CodyJon/dreame-ap10-integration
```

Questa integrazione deve usare, almeno inizialmente, la **Dreame Cloud API** tramite credenziali Dreamehome. Non assumere l’esistenza di una API locale stabile.

---

# Obiettivo generale

Implementare una custom integration Home Assistant per il modello:

```text
dreame.fan.u2519
```

con approccio incrementale:

1. **Fase 1 — integrazione minima stabile**
   - login cloud Dreamehome;
   - discovery del dispositivo;
   - lettura stato base;
   - controllo accensione/spegnimento;
   - controllo velocità;
   - modalità base;
   - sensori/switch semplici se immediatamente mappabili.

2. **Fase 2 — reverse engineering property map completa**
   - discovery sistematica di `siid`, `piid`, `aiid`;
   - logging dettagliato;
   - confronto diff pre/post comando da app Dreamehome;
   - costruzione tabella stabile delle proprietà MF10.

3. **Fase 3 — funzioni avanzate**
   - oscillazione testa;
   - oscillazione pale sinistra/destra;
   - timer;
   - display/light;
   - child lock;
   - buzzer;
   - modalità sleep/natural/smart/custom;
   - eventuali button/action per reset oscillazione o sync posizione.

4. **Fase 4 — hardening e packaging HACS-ready**
   - config flow robusto;
   - error handling;
   - retries;
   - diagnostics;
   - logging sicuro;
   - README completo;
   - struttura HACS compatibile.

---

# Vincoli importanti

## Non rompere Home Assistant

L’integrazione deve essere conforme alle best practice Home Assistant:

- usare `DataUpdateCoordinator`;
- non bloccare l’event loop;
- usare chiamate async o executor dove necessario;
- gestire timeout e rate limit;
- evitare polling troppo aggressivo;
- non salvare password in chiaro oltre a quanto gestito da config entries/secrets;
- non loggare token, password, refresh token o dati sensibili.

## Non dare per scontata la property map

Il modello `dreame.fan.u2519` può avere property map diversa da AP10/PM10.

Non hardcodare in modo definitivo valori presunti senza discovery.

Puoi creare una property map provvisoria, ma deve essere chiaramente separata da quella definitiva:

```python
MF10_PROPERTY_CANDIDATES = {...}
MF10_PROPERTY_MAP = {...}
```

## Integrazione cloud-first

La prima versione deve puntare alla Dreame Cloud API.

Non investire troppo tempo in:

- API locale non documentata;
- sniffing firmware;
- BLE reverse engineering;
- IR/RF remote control.

Questi possono essere considerati fallback, ma non sono lo scopo primario.

---

# Architettura desiderata

Struttura proposta:

```text
custom_components/
  dreame_mf10/
    __init__.py
    manifest.json
    const.py
    config_flow.py
    coordinator.py
    dreame_cloud.py
    fan.py
    sensor.py
    switch.py
    select.py
    number.py
    button.py
    diagnostics.py
    strings.json
    translations/
      en.json
      it.json
```

Nome dominio Home Assistant:

```python
DOMAIN = "dreame_mf10"
```

Model supportato:

```python
MODEL_MF10 = "dreame.fan.u2519"
SUPPORTED_MODELS = {MODEL_MF10}
```

---

# FASE 1 — Integrazione minima stabile

## Obiettivo della fase 1

Avere una custom integration installabile in Home Assistant che permetta almeno:

- autenticazione Dreamehome;
- discovery del dispositivo `dreame.fan.u2519`;
- creazione entità `fan`;
- lettura stato online/offline;
- accensione/spegnimento o pseudo-spegnimento sicuro;
- controllo velocità 1–10 tramite percentuale Home Assistant;
- polling stato base.

Questa fase deve privilegiare stabilità e osservabilità rispetto alla copertura completa delle funzioni.

---

## Deliverable fase 1

### 1. Repository funzionante

Crea un repository con struttura installabile in:

```text
/config/custom_components/dreame_mf10
```

Il repository deve contenere almeno:

```text
custom_components/dreame_mf10/manifest.json
custom_components/dreame_mf10/__init__.py
custom_components/dreame_mf10/config_flow.py
custom_components/dreame_mf10/coordinator.py
custom_components/dreame_mf10/dreame_cloud.py
custom_components/dreame_mf10/fan.py
custom_components/dreame_mf10/const.py
README.md
```

---

### 2. Config flow

Implementa config flow da UI Home Assistant.

Campi richiesti:

```text
Username / email Dreamehome
Password Dreamehome
Region
Optional: device model filter
Optional: polling interval
```

La regione deve supportare almeno:

```text
eu
cn
us
sg
ru
```

Default consigliato per l’utente:

```text
eu
```

Il config flow deve:

1. validare credenziali;
2. fare login;
3. scaricare lista dispositivi;
4. filtrare dispositivi con model `dreame.fan.u2519`;
5. se un solo device viene trovato, creare automaticamente la config entry;
6. se più device vengono trovati, permettere selezione;
7. se nessun device viene trovato, mostrare errore chiaro.

Errori da gestire:

```text
invalid_auth
cannot_connect
no_supported_devices
unknown
```

---

### 3. Dreame Cloud client

Implementa o adatta un client cloud in:

```text
dreame_cloud.py
```

Funzioni minime richieste:

```python
async def async_login(username: str, password: str, region: str) -> None
async def async_get_devices() -> list[dict]
async def async_get_properties(did: str | int, properties: list[dict]) -> dict
async def async_set_properties(did: str | int, properties: list[dict]) -> dict
async def async_call_action(did: str | int, siid: int, aiid: int, params: list | None = None) -> dict
```

Se il codice esistente è sincrono, wrappalo correttamente usando executor o converti in async.

Non loggare token o password.

---

### 4. DataUpdateCoordinator

Implementa un coordinator in:

```text
coordinator.py
```

Responsabilità:

- tenere stato device;
- eseguire polling;
- leggere property note;
- esporre dati normalizzati alle entità;
- gestire unavailable se cloud/device non risponde;
- fare refresh immediato dopo un comando.

Polling iniziale consigliato:

```python
SCAN_INTERVAL = timedelta(seconds=30)
```

Non scendere sotto i 10 secondi nella fase 1.

---

### 5. Fan entity

Implementa una `FanEntity` in:

```text
fan.py
```

Entità principale:

```text
fan.dreame_mf10
```

Funzioni Home Assistant richieste:

```python
@property
def is_on(self) -> bool | None

@property
def percentage(self) -> int | None

@property
def percentage_step(self) -> int

async def async_turn_on(self, percentage: int | None = None, preset_mode: str | None = None, **kwargs)

async def async_turn_off(self, **kwargs)

async def async_set_percentage(self, percentage: int)
```

Mapping velocità:

```text
MF10 speed 1  -> HA 10%
MF10 speed 2  -> HA 20%
MF10 speed 3  -> HA 30%
MF10 speed 4  -> HA 40%
MF10 speed 5  -> HA 50%
MF10 speed 6  -> HA 60%
MF10 speed 7  -> HA 70%
MF10 speed 8  -> HA 80%
MF10 speed 9  -> HA 90%
MF10 speed 10 -> HA 100%
```

Implementa utility:

```python
def speed_to_percentage(speed: int | None) -> int | None:
    if speed is None:
        return None
    return max(10, min(100, int(speed) * 10))


def percentage_to_speed(percentage: int) -> int:
    if percentage <= 0:
        return 0
    return max(1, min(10, round(percentage / 10)))
```

Nota: se `percentage == 0`, Home Assistant può interpretarlo come off. Gestire coerentemente.

---

## Property map provvisoria fase 1

La property map non è nota. Devi implementare discovery/logging e usare una mappa provvisoria flessibile.

Partire dai candidati:

```python
MF10_PROPERTY_CANDIDATES = {
    "power": [
        {"siid": 2, "piid": 1},
    ],
    "mode": [
        {"siid": 2, "piid": 2},
        {"siid": 2, "piid": 3},
    ],
    "speed": [
        {"siid": 2, "piid": 4},
        {"siid": 2, "piid": 5},
    ],
    "temperature": [
        {"siid": 3, "piid": 1},
        {"siid": 3, "piid": 2},
        {"siid": 3, "piid": 3},
    ],
    "display_light": [
        {"siid": 6, "piid": 5},
        {"siid": 6, "piid": 8},
    ],
    "child_lock": [
        {"siid": 6, "piid": 7},
    ],
}
```

Questi valori sono solo candidati. Devi validarli empiricamente.

---

## Modalità discovery fase 1

Aggiungi una modalità debug opzionale abilitabile da `configuration.yaml` o da opzione config entry.

Esempio:

```yaml
dreame_mf10:
  debug_property_scan: true
```

Oppure via options flow:

```text
Enable property scan diagnostics
```

Quando abilitata, l’integrazione deve provare a leggere range di property candidate:

```text
siid=2 piid=1..20
siid=3 piid=1..20
siid=4 piid=1..20
siid=5 piid=1..20
siid=6 piid=1..20
siid=7 piid=1..20
siid=8 piid=1..20
```

Output log desiderato:

```text
[Dreame MF10] Property scan result: siid=2 piid=1 value=True code=0
[Dreame MF10] Property scan result: siid=2 piid=4 value=3 code=0
[Dreame MF10] Property scan result: siid=3 piid=1 value=24 code=0
[Dreame MF10] Property scan result: siid=6 piid=7 value=False code=0
```

Ignora o logga a debug le property con errore.

Non generare errori fatali se una property non esiste.

---

## Script di property scan standalone

Oltre all’integrazione, crea uno script CLI opzionale:

```text
tools/scan_properties.py
```

Input:

```bash
python tools/scan_properties.py \
  --username "$DREAME_USERNAME" \
  --password "$DREAME_PASSWORD" \
  --region eu \
  --did -115387050 \
  --model dreame.fan.u2519
```

Output JSON:

```json
{
  "model": "dreame.fan.u2519",
  "did": "-115387050",
  "scan": [
    {"siid": 2, "piid": 1, "value": true, "code": 0},
    {"siid": 2, "piid": 4, "value": 3, "code": 0}
  ]
}
```

Aggiungi anche una opzione:

```bash
--output mf10_property_scan.json
```

---

## Procedura manuale di discovery

Documenta nel README una procedura precisa:

### Step 1 — snapshot iniziale

```bash
python tools/scan_properties.py --output before.json ...
```

### Step 2 — cambia una funzione da Dreamehome

Esempi:

```text
- cambia velocità da 3 a 8
- cambia modalità da Normal a Sleep
- accendi/spegni display
- attiva/disattiva child lock
- avvia oscillazione
```

### Step 3 — snapshot dopo

```bash
python tools/scan_properties.py --output after.json ...
```

### Step 4 — diff

Crea script:

```text
tools/diff_properties.py
```

Uso:

```bash
python tools/diff_properties.py before.json after.json
```

Output desiderato:

```text
Changed properties:
- siid=2 piid=4: 3 -> 8
```

---

## Gestione ON/OFF

Verifica empiricamente se il device può essere riacceso da remoto dopo spegnimento reale.

Procedura:

1. Spegni da app Dreamehome.
2. Aspetta 60 secondi.
3. Prova a riaccendere da app.
4. Prova a riaccendere da integrazione.
5. Verifica se device rimane online.

Implementa due strategie:

```python
POWER_OFF_MODE_REAL = "real"
POWER_OFF_MODE_SOFT = "soft"
```

Opzione configurabile:

```text
Off behavior:
- real power off
- soft off / sleep speed 1
```

Default prudente:

```text
real power off
```

Se si scopre che il device va in deep standby e non si risveglia via cloud, cambiare default a:

```text
soft off / sleep speed 1
```

---

# FASE 1 — criteri di accettazione

La fase 1 è completata quando:

- Home Assistant carica l’integrazione senza errori;
- il config flow accetta credenziali Dreamehome valide;
- il device `dreame.fan.u2519` viene scoperto;
- viene creata almeno una entità `fan`;
- lo stato online/offline è visibile;
- è possibile accendere il ventilatore da Home Assistant;
- è possibile spegnerlo o metterlo in soft-off;
- è possibile impostare velocità 1–10 tramite percentuale;
- il polling aggiorna lo stato dopo modifiche fatte da app Dreamehome;
- i log non contengono password/token;
- l’integrazione non blocca il loop di Home Assistant.

---

# FASE 2 — Property map completa

## Obiettivo fase 2

Costruire una property map affidabile per `dreame.fan.u2519`.

Output finale desiderato:

```python
MF10_PROPERTY_MAP = {
    "power": {"siid": ?, "piid": ?, "type": "property"},
    "power_action": {"siid": ?, "aiid": ?, "type": "action"},
    "speed": {"siid": ?, "piid": ?, "type": "property", "range": [1, 10]},
    "mode": {"siid": ?, "piid": ?, "type": "property", "values": {...}},
    "temperature": {"siid": ?, "piid": ?, "type": "property", "unit": "°C"},
    "display_light": {"siid": ?, "piid": ?, "type": "property"},
    "child_lock": {"siid": ?, "piid": ?, "type": "property"},
    "buzzer": {"siid": ?, "piid": ?, "type": "property"},
    "head_oscillation": {"siid": ?, "piid": ?, "type": "property"},
    "head_angle": {"siid": ?, "piid": ?, "type": "property"},
    "left_blade_angle": {"siid": ?, "piid": ?, "type": "property"},
    "right_blade_angle": {"siid": ?, "piid": ?, "type": "property"},
    "timer": {"siid": ?, "piid": ?, "type": "property"},
}
```

---

## Discovery matrix

Esegui una matrice di test manuale.

Per ogni comando:

1. salva snapshot prima;
2. esegui comando da app Dreamehome;
3. salva snapshot dopo;
4. confronta diff;
5. ripeti almeno due volte;
6. verifica se Home Assistant può scrivere la stessa property;
7. documenta risultato.

Tabella da compilare nel README o in `docs/property_map.md`:

| Funzione | Azione manuale | Property cambiata | Tipo | Valori osservati | Scrivibile da HA | Note |
|---|---|---|---|---|---|---|
| Power | App ON/OFF | siid=?, piid=? | property/action | true/false | sì/no | |
| Speed | 1→10 | siid=?, piid=? | property | 1..10 | sì/no | |
| Mode | Normal→Sleep | siid=?, piid=? | property | ? | sì/no | |
| Display | ON/OFF | siid=?, piid=? | property | true/false | sì/no | |
| Child lock | ON/OFF | siid=?, piid=? | property | true/false | sì/no | |
| Buzzer | ON/OFF | siid=?, piid=? | property | true/false | sì/no | |
| Temperature | Osservazione | siid=?, piid=? | read-only | °C | no | |
| Head oscillation | ON/OFF | siid=?, piid=? | property/action | ? | sì/no | |
| Left blade | cambia angolo | siid=?, piid=? | property/action | ? | sì/no | |
| Right blade | cambia angolo | siid=?, piid=? | property/action | ? | sì/no | |
| Timer | imposta timer | siid=?, piid=? | property/action | minuti/ore | sì/no | |

---

## Action discovery

Non tutte le funzioni potrebbero essere property scrivibili. Alcune potrebbero richiedere action MiOT-style.

Implementa una modalità sperimentale per testare action candidate:

```text
siid=2 aiid=1..10
siid=3 aiid=1..10
siid=4 aiid=1..10
siid=5 aiid=1..10
siid=6 aiid=1..10
siid=7 aiid=1..10
```

Attenzione: non chiamare action alla cieca in automatico all’avvio dell’integrazione.

Le action vanno testate solo manualmente tramite script CLI esplicito:

```text
tools/call_action.py
```

Uso:

```bash
python tools/call_action.py \
  --username "$DREAME_USERNAME" \
  --password "$DREAME_PASSWORD" \
  --region eu \
  --did -115387050 \
  --siid 2 \
  --aiid 3
```

Il README deve avvertire chiaramente:

```text
Do not brute-force actions on a real device unless you understand the risk. Actions may move fan blades, reset settings, start oscillation, power off the device, or trigger unknown behavior.
```

---

# FASE 3 — Funzioni avanzate

## Entità aggiuntive

Una volta consolidata la property map, aggiungi entità aggiuntive.

### Sensor

File:

```text
sensor.py
```

Entità possibili:

```text
sensor.dreame_mf10_temperature
sensor.dreame_mf10_firmware_version
sensor.dreame_mf10_plugin_version
sensor.dreame_mf10_wifi_rssi
```

Solo se le property sono disponibili.

---

### Switch

File:

```text
switch.py
```

Switch possibili:

```text
switch.dreame_mf10_display_light
switch.dreame_mf10_child_lock
switch.dreame_mf10_buzzer
switch.dreame_mf10_head_oscillation
switch.dreame_mf10_left_blade_oscillation
switch.dreame_mf10_right_blade_oscillation
```

---

### Select

File:

```text
select.py
```

Select possibili:

```text
select.dreame_mf10_mode
```

Valori da verificare empiricamente.

Possibili nomi UI:

```text
Normal
Natural
Sleep
Smart
Custom
```

Non hardcodare label se non corrispondono ai valori reali.

---

### Number

File:

```text
number.py
```

Number possibili:

```text
number.dreame_mf10_speed_level
number.dreame_mf10_head_angle
number.dreame_mf10_left_blade_angle
number.dreame_mf10_right_blade_angle
number.dreame_mf10_timer
```

Per `speed_level`, valutare se è ridondante rispetto a `fan.percentage`. Può essere utile in fase debug, ma opzionale per versione finale.

---

### Button

File:

```text
button.py
```

Button possibili:

```text
button.dreame_mf10_reset_oscillation
button.dreame_mf10_sync_position
button.dreame_mf10_property_scan
```

`property_scan` solo se sicuro e non invasivo.

---

## Preset mode nella FanEntity

Dopo discovery modalità, implementare:

```python
@property
def preset_modes(self) -> list[str]:
    return ["Normal", "Natural", "Sleep", "Smart", "Custom"]

@property
def preset_mode(self) -> str | None:
    ...

async def async_set_preset_mode(self, preset_mode: str) -> None:
    ...
```

I valori reali devono essere mappati da property map:

```python
MF10_MODE_MAP = {
    0: "Normal",
    1: "Natural",
    2: "Sleep",
    3: "Smart",
    4: "Custom",
}
```

Questa mappa è solo un esempio: validare con discovery.

---

# FASE 4 — Hardening, qualità e HACS

## Diagnostics

Implementa `diagnostics.py`.

Output diagnostico deve includere:

```text
model
firmware_version
plugin_version
region
supported_features
known_property_map
last_update_success
last_update_error_type
```

Deve escludere:

```text
password
token
refresh_token
session cookies
raw auth headers
```

---

## Options flow

Aggiungi options flow per:

```text
Polling interval
Debug property scan
Off behavior: real/soft
Enable experimental entities
```

Valori consigliati:

```text
polling interval default: 30s
min polling interval: 10s
max polling interval: 300s
debug property scan default: false
experimental entities default: false
off behavior default: real, configurable
```

---

## README

Il README deve contenere:

1. descrizione integrazione;
2. dispositivi supportati;
3. modello supportato `dreame.fan.u2519`;
4. requisiti;
5. installazione manuale;
6. installazione HACS custom repository;
7. configurazione;
8. entità esposte;
9. limitazioni note;
10. procedura property scan;
11. procedura diff;
12. troubleshooting;
13. nota sicurezza token/log;
14. changelog.

---

## Logging

Usa logger dedicato:

```python
_LOGGER = logging.getLogger(__name__)
```

Livelli:

```text
INFO: setup, discovered device, created entities
DEBUG: raw property values, polling details
WARNING: recoverable errors, unsupported properties
ERROR: login failure, unrecoverable API errors
```

Non loggare mai segreti.

---

## Testing minimo

Aggiungi test unitari almeno per:

```text
speed_to_percentage
percentage_to_speed
mode mapping
property parser
redaction diagnostics
```

Esempio test:

```python
def test_percentage_to_speed():
    assert percentage_to_speed(10) == 1
    assert percentage_to_speed(55) in (5, 6)
    assert percentage_to_speed(100) == 10
```

---

# Pseudocodice consigliato

## const.py

```python
DOMAIN = "dreame_mf10"

MODEL_MF10 = "dreame.fan.u2519"
SUPPORTED_MODELS = {MODEL_MF10}

CONF_REGION = "region"
CONF_POLLING_INTERVAL = "polling_interval"
CONF_OFF_BEHAVIOR = "off_behavior"
CONF_DEBUG_PROPERTY_SCAN = "debug_property_scan"

DEFAULT_REGION = "eu"
DEFAULT_POLLING_INTERVAL = 30
MIN_POLLING_INTERVAL = 10

OFF_BEHAVIOR_REAL = "real"
OFF_BEHAVIOR_SOFT = "soft"

MF10_SPEED_MIN = 1
MF10_SPEED_MAX = 10
```

---

## utils.py

```python
def speed_to_percentage(speed: int | None) -> int | None:
    if speed is None:
        return None
    try:
        speed = int(speed)
    except (TypeError, ValueError):
        return None
    if speed <= 0:
        return 0
    return max(10, min(100, speed * 10))


def percentage_to_speed(percentage: int | None) -> int:
    if percentage is None:
        return 1
    if percentage <= 0:
        return 0
    return max(1, min(10, round(percentage / 10)))
```

---

## coordinator.py

```python
class DreameMF10Coordinator(DataUpdateCoordinator):
    def __init__(self, hass, client, device, options):
        super().__init__(
            hass,
            _LOGGER,
            name=f"Dreame MF10 {device.get('did')}",
            update_interval=timedelta(seconds=options.polling_interval),
        )
        self.client = client
        self.device = device
        self.did = device["did"]
        self.model = device.get("model")
        self.state = {}

    async def _async_update_data(self):
        try:
            props = await self.client.async_get_properties(
                self.did,
                self._properties_to_poll(),
            )
            self.state = self._parse_properties(props)
            return self.state
        except Exception as err:
            raise UpdateFailed(str(err)) from err

    def _properties_to_poll(self):
        # Return known properties if map is confirmed.
        # During phase 1, return candidate properties and tolerate failures.
        ...

    def _parse_properties(self, props):
        # Normalize raw Dreame/MiOT-like response into:
        # {
        #   "is_on": bool | None,
        #   "speed": int | None,
        #   "mode": int | None,
        #   "temperature": float | None,
        # }
        ...
```

---

## fan.py

```python
class DreameMF10Fan(CoordinatorEntity, FanEntity):
    _attr_name = "Dreame MF10"
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED |
        FanEntityFeature.TURN_ON |
        FanEntityFeature.TURN_OFF
    )
    _attr_percentage_step = 10

    @property
    def is_on(self):
        return self.coordinator.data.get("is_on")

    @property
    def percentage(self):
        return speed_to_percentage(self.coordinator.data.get("speed"))

    async def async_set_percentage(self, percentage):
        speed = percentage_to_speed(percentage)
        if speed <= 0:
            await self.async_turn_off()
            return
        await self.coordinator.async_set_speed(speed)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        await self.coordinator.async_turn_on()
        if percentage is not None:
            await self.async_set_percentage(percentage)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_turn_off()
        await self.coordinator.async_request_refresh()
```

---

# Note operative per il coding agent

## Prima cosa da fare

Non scrivere subito tutte le entità.

Prima fai funzionare:

```text
login → discovery → polling → fan entity → speed control
```

Solo dopo aggiungi switch/select/number/button.

---

## Non fingere supporto completo

Se una funzione non è stata verificata, non esporla come entità stabile.

Usa nomi come:

```text
experimental
candidate
unknown
```

solo nei tool diagnostici, non nell’interfaccia finale dell’utente.

---

## Backward compatibility

Prevedi che in futuro possano essere aggiunti altri modelli Dreame fan:

```python
MODEL_CAPABILITIES = {
    "dreame.fan.u2519": MF10_CAPABILITIES,
}
```

Non scrivere codice che renda impossibile supportare altri model ID.

---

# Output richiesto al coding agent

Alla fine della fase 1 devi produrre:

1. codice della custom integration;
2. istruzioni installazione manuale;
3. istruzioni configurazione Home Assistant;
4. script `scan_properties.py`;
5. script `diff_properties.py`;
6. log di esempio atteso;
7. elenco property già confermate;
8. elenco property candidate ancora da validare;
9. lista limitazioni note.

Alla fine della fase 2 devi produrre:

1. `docs/property_map.md` completo;
2. mappa Python `MF10_PROPERTY_MAP` aggiornata;
3. test manuali documentati;
4. funzioni base rese stabili.

Alla fine della fase 3 devi produrre:

1. entità avanzate;
2. README aggiornato;
3. opzioni sperimentali disattivabili;
4. diagnostica Home Assistant.

---

# Roadmap consigliata

## Milestone 0 — Setup repo

- creare struttura integrazione;
- definire domain;
- manifest;
- config flow placeholder;
- README iniziale.

## Milestone 1 — Cloud login e discovery

- adattare client Dreame cloud;
- login con regione;
- get devices;
- filtro `dreame.fan.u2519`;
- config entry.

## Milestone 2 — Polling property candidate

- coordinator;
- scan proprietà candidate;
- logging debug;
- tolleranza errori.

## Milestone 3 — Fan entity minima

- is_on;
- percentage;
- turn_on;
- turn_off;
- set_percentage.

## Milestone 4 — Script discovery

- `scan_properties.py`;
- `diff_properties.py`;
- documentazione procedura.

## Milestone 5 — Property map confermata

- test manuali;
- aggiornamento mappa;
- riduzione property polling solo a quelle note.

## Milestone 6 — Entità avanzate

- sensor;
- switch;
- select;
- number;
- button.

## Milestone 7 — Packaging

- README finale;
- HACS compatibility;
- diagnostics;
- translations;
- tests.

---

# Definizione di “done” per la prima release utile

La prima release utile è considerata pronta quando l’utente può installare l’integrazione in Home Assistant e controllare il Dreame MF10 almeno così:

```text
- vedere se il ventilatore è disponibile;
- accenderlo;
- spegnerlo o metterlo in soft-off;
- impostare velocità 1–10;
- vedere aggiornarsi lo stato anche dopo comandi da Dreamehome;
- consultare log diagnostici per continuare la mappatura.
```

Tutto il resto è migliorativo, non bloccante.

---

# Nota finale

Lavora in modo incrementale e verificabile.

La parte più rischiosa non è Home Assistant: è la mappatura corretta delle proprietà Dreame/MiOT-style del modello `dreame.fan.u2519`.

Quindi il successo del progetto dipende da:

```text
1. far comparire il device via cloud;
2. leggere property candidate senza crash;
3. costruire diff affidabili;
4. confermare una property alla volta;
5. esporre in Home Assistant solo ciò che è stato validato.
```

