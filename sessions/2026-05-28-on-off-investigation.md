# Sessione 2026-05-28 — Investigazione on/off: analisi PM10 repo + test action

## Obiettivo
Ripartire da zero sull'on/off del MF10, analizzando il repo `shaunsingh/dreame-pm10-integration`
(purificatore PM10, modello `dreame.airp.cvf24a`) come riferimento.

## Cosa abbiamo fatto

### 1. Analisi profonda di `shaunsingh/dreame-pm10-integration`
Repository clonato in `tmp/dreame-pm10-integration/`.

Architettura identica alla nostra per quanto riguarda:
- Endpoint cloud: `https://{region}.iot.dreame.tech:13267`
- Auth headers: stesso salt, stesso `Authorization: Basic`, stesso `Dreame-Auth`
- Struttura `sendCommand`: identica

**Differenza critica — on/off sul PM10:**
Il PM10 usa `action(siid=2, aiid=3)` come toggle power. Costante nel codice:
```python
ACTION_TOGGLE_POWER = (2, 3)  # (siid, aiid)
```
Funziona perché sul `dreame.airp.cvf24a` quella action significa "toggle power".

### 2. Test action siid=2, aiid=3 sul MF10 — RISULTATO: WiFi reset

Adattato `tools/call_action.py` con `--toggle-power` e `--read-prop`.

Eseguito `--read-prop --siid 2 --piid 1`:
- **Risultato: `value=2` (STANDBY)** — property leggibile, device in standby

Eseguito `--toggle-power` (che chiama action siid=2, aiid=3):
- **Risultato: code=80001 dal relay, ma il device si è disconnesso fisicamente**
- Il device ha ricevuto il comando via MQTT, lo ha eseguito (WiFi reset), ma non ha fatto ack in tempo → relay restituisce 80001 ma l'action è stata eseguita

⚠️ **Device ora "Disconnesso" nell'app Dreame. Richiede re-pairing fisico.**

### 3. Chiarimento comportamento standby MF10

Il proprietario conferma:
- **In standby**: device connesso WiFi, MQTT attivo, riceve TUTTI i comandi tranne on/off
- **Disconnesso** (stato attuale): WiFi reset fisico, nessun comando possibile, richiede re-pairing

Quindi il 80001 su `set_properties siid=2 piid=1 value=1` che avevamo visto in precedenza
NON era perché il device non ascoltava — il device ascoltava, ma `piid=1` è **read-only**.

### 4. Conferma da snapshot esistenti (2026-05-22)

Diff tra `after-power-on.json` e `after-power-off.json`:

| siid | piid | ON | STANDBY | Note |
|------|------|----|---------|------|
| 2 | 1 | 1 | 2 | Power state — **read-only** |
| 2 | 4 | 8 | 6 | Fan speed — cambia perché riparte dalla vel. precedente |

Solo questi due cambiano. Confermato che `piid=1` è un indicatore aggiornato dal device,
non una property scrivibile.

### 5. Conclusione su PM10 vs MF10

| Device | Model | `siid=2, aiid=3` |
|--------|-------|-----------------|
| PM10 Air Purifier | `dreame.airp.cvf24a` | ✅ Toggle power |
| MF10 Fan | `dreame.fan.u2519` | ❌ WiFi reset |

Le action MiOT hanno significato **device-specific**. Non si può portare la property map
di un purificatore su un ventilatore.

### 6. Ricerca su miot-spec.org — pista concreta

I modelli Dreame fan registrati più simili all'MF10 (`dreame.fan.p2018`, `dreame.fan.l2146`)
hanno una property **separata** per on/off:

| siid | piid | Tipo | Accesso | Label |
|------|------|------|---------|-------|
| 11 | 5 | bool | **write-only** | "on-off" / 开/关机 |

Questa è **distinta** da `siid=2, piid=1` (read-only power state indicator).

Il modello `dreame.fan.p2138u` ha invece `siid=17, piid=1` "smart-on-off" write-only.

**Il modello `dreame.fan.u2519` NON è registrato su miot-spec.org.**

## Stato del codice

`tools/call_action.py` aggiornato con:
- `--read-prop --siid S --piid P` — legge valore corrente di una property
- `--toggle-power` — ora BLOCCATO (causa reset WiFi confermato)
- Warning aggiornato: aiid=1/2/3 su siid=2 sono tutti pericolosi sul MF10

## Test da eseguire al re-pairing (ordine consigliato)

### Pre-condizione
Device fisicamente riacceso e re-paired. Verificare con:
```bash
python3 tools/call_action.py --read-prop --siid 2 --piid 1
# Atteso: value=1 (on) o value=2 (standby)
```

### Test 1 — siid=11, piid=5 (candidato principale)
```bash
# Leggi prima (verifica che la property esista)
python3 tools/call_action.py --read-prop --siid 11 --piid 5

# Se esiste, prova off con device ON
python3 tools/call_action.py --set-prop --siid 11 --piid 5 --value false

# Se funziona, prova on da standby
python3 tools/call_action.py --set-prop --siid 11 --piid 5 --value true
```

### Test 2 — siid=17, piid=1 (candidato secondario)
```bash
python3 tools/call_action.py --read-prop --siid 17 --piid 1
python3 tools/call_action.py --set-prop --siid 17 --piid 1 --value true   # on
python3 tools/call_action.py --set-prop --siid 17 --piid 1 --value false  # off
```

### Test 3 — set_properties siid=2, piid=1 con device ON
Con device fisicamente acceso, provare la scrittura diretta:
```bash
python3 tools/call_action.py --set-prop --siid 2 --piid 1 --value 2  # off
# Se funziona: da standby provare --value 1 per riaccendere
```
Nota: in precedenza ha dato 80001 con device in standby. Con device ON potrebbe funzionare.

### Test 4 — scan property map su siid=11 e siid=17
Se i test sopra non danno risultati, eseguire uno scan esteso:
```bash
python3 tools/scan_properties.py --siid-min 11 --siid-max 20 --label extended-scan
```

## Blocchi attuali
- Device disconnesso (WiFi reset da aiid=3) — richiede re-pairing fisico
- `dreame.fan.u2519` non registrato su miot-spec.org
- Nessuna integrazione pubblica nota per questo modello

## Note architetturali
- Il cloud relay Dreame applica una distinzione funzionale:
  - `get_properties` → legge cache cloud → funziona sempre
  - `set_properties` / `action` → richiede ack real-time dal device → 80001 se non risponde
- Il device in standby (piid=1=2) è connesso WiFi e risponde a set/action per tutto tranne power
- Il 80001 con device in standby su siid=2/piid=1 indica che la property è read-only,
  non che il device sia irraggiungibile
