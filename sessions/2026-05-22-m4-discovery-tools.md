# 2026-05-22 — M4 (anticipato): tool di discovery property map

## Contesto

Seconda sessione di sviluppo. M0 chiusa (smoke test verde, push su `main` con commit `57884cc`). L'utente ha scelto di **invertire l'ordine roadmap** e fare prima M4 (`tools/scan_properties.py` + `tools/diff_properties.py`) prima di M2 (coordinator) e M3 (fan entity). Razionale: `MF10_PROPERTY_CANDIDATES` in `const.py` sono guess basati su pattern AP10 (siid 2 power/mode/speed, siid 3 temp, siid 6 lock) — costruirvi sopra coordinator/entity senza validazione = entity rotte. Validare la mappa offline via CLI è più rapido (no riavvio HA, no UI) e produce snapshot riutilizzabili per docs.

## Cosa fatto

- Piano [plans/phase1-milestone4-discovery-tools.md](../plans/phase1-milestone4-discovery-tools.md) scritto con criteri di successo, task list, rischi, scope exclusion (`call_action.py` rinviato per pericolosità: può muovere pale del fan).
- **Advisor gate #1** (prima di scrivere codice) — issue applicate al piano: batch-size default 1 invece di 10, pre-flight check su `(2,1)`, `--label` obbligatorio invece di `<slug>` indefinito, MAC nascosto di default, `example.json` differito a dopo primo scan reale.
- Implementati:
  - [tools/scan_properties.py](../tools/scan_properties.py) — async aiohttp CLI: env vars per creds, device listing se `--did` mancante, pre-flight check sulla shape della response, scan loop tollerante con `--batch-size` (default 1) + `--batch-delay-ms` (default 200ms), output JSON in `research/snapshots/<UTC-ts>-<label>.json`. Riusa `DreameCloud` da `custom_components.dreame_mf10.dreame_cloud` via `sys.path` injection (esecuzione da repo root).
  - [tools/diff_properties.py](../tools/diff_properties.py) — pure stdlib: diff `(siid, piid) → value`, skip errori per default (`--include-errors` per mostrarli), output testo o `--json`.
  - [tools/README.md](../tools/README.md) — workflow before/after, esempi, security notes.
- Smoke test:
  - `py_compile` su entrambi → OK.
  - `diff_properties.py` testato con snapshot sintetici in `/tmp` (cambi rilevati, errori skippati, output testo e JSON corretti).
  - `scan_properties.py --help` non eseguibile localmente (`aiohttp` non installato fuori da HA). Runtime test → utente alla prima discovery reale.

## Decisioni

1. **Batch-size default = 1, non 10** (su advisor): non sappiamo ancora se Dreame restituisce errori per-item in un batch (envelope OK) o rigetta l'intero batch (envelope `code != 0`). Difensivo: 1 property per request. Si alza dopo verifica empirica.
2. **`--label` obbligatorio** (su advisor): forza il workflow before/after fin dal naming del file (`2026-05-22-160230-before-speed-change.json`).
3. **`example.json` differito**: redactare una shape ipotetica è rumore. Si scrive dopo aver visto la prima response reale di `listV2` (potrebbe contenere campi sorpresa).
4. **Esecuzione**: `python tools/scan_properties.py …` da repo root, no `tools/__init__.py`. Ridotto a una modalità sola (advisor: "scegli una e basta").
5. **MAC nascosto di default nel device listing**: visibile solo con `-v`. Repo pubblico → meglio non incoraggiare a postare output con MAC nei bug report.
6. **`tools/call_action.py` rimandato**: action MiOT possono muovere pale / spegnere device. Va in commit separato con confirm prompt + `--yes` flag. Non in M4.
7. **Imports reuse `DreameCloud`**: nessuna duplicazione del client, `sys.path` injection accettata come trade-off vs. fare `tools/` un pacchetto installabile (overhead inutile per uso interno).

## Blocchi / domande aperte

- **Runtime test rinviato all'utente**: serve `aiohttp` + credenziali Dreame. Step pratici per chiudere M4 davvero:
  1. Esportare `DREAME_USERNAME` / `DREAME_PASSWORD`.
  2. `python tools/scan_properties.py --label list` → conferma che la device list ritorna `dreame.fan.u2519`.
  3. `python tools/scan_properties.py --label before-test --did -115387050` → scan completo (~60s con batch-size 1).
  4. Esaminare il JSON: serve verificare (a) se le piid invalide ritornano `code != 0` con la response a livello envelope OK (= tolleranza per-property funziona), (b) se ci sono campi sensibili nella response che non avevo previsto.
  5. Se (a) OK → bumpare `--batch-size 10` per scan futuri ed eseguire un ciclo before/after vero (es. cambio di velocità dall'app).
  6. Scrivere `research/snapshots/example.json` redacted dal primo scan reale.
- **Range di scan**: default `siid 1..10, piid 1..30`. Da rivedere se i risultati mostrano property fuori range (improbabile per un fan).

## Discovery property map — risultati sessione

### Bug trovati al primo run reale

1. **HTTP 404 su sendCommand** — root cause: endpoint Dreame non è `/dreame-iot-com/device/sendCommand`
   ma `/dreame-iot-com-<prefix>/device/sendCommand`, dove `<prefix>` è il primo segmento di
   `bindDomain` (campo `"bindDomain"` nel record device da `listV2`).
   Ex: `bindDomain=10000.mt.eu.iot.dreame.tech:19973` → `host_prefix="-10000"`.
   Fix applicato a `dreame_cloud.py` + `scan_properties.py`.

2. **Brute-force range scan impraticabile** — latenza ~8s/request per property sconosciute
   (backend forwarda al device fisico per discovery). 300 property × 8s = ~40 minuti.
   Dreame rigetta l'intera envelope con `code=80001` per property inesistenti (no per-item
   tolerance). Pivot: aggiunto `--candidates-only` (default raccomandato), scan solo ~11
   property in ~36s. Brute-force rimane opt-in con warning.

### Cicli before/after eseguiti

| Test | (siid,piid) changed | finding |
|------|---------------------|---------|
| OFF → ON | (2,1): 2→1, (2,4): 6→8 | power=ON=1, power=OFF=2 |
| ON → OFF | (2,1): 1→2, (2,4): 8→6 | confermato |
| → Sleep mode | (2,3): 0→2, (2,4): 8→1 | mode sleep=2 |
| → Manuale speed 5 | (2,3): 2→3, (2,4): 1→5 | mode manual=3, speed=(2,4) confermato |
| → Naturale | (2,3): 3→7, (2,4): 5→2 | mode natural=7 |
| → Potente | (2,3): 7→1, (2,4): 2→10 | mode powerful=1 |
| Child lock ON | (2,5): 0→1 | child_lock=(2,5) |
| Child lock OFF | (2,5): 1→0 | confermato, unica variazione |

Temperatura (3,2) = sensore ambient confermato (drift naturale tra scan, indipendente da azioni).

### Property map risultante

| property | siid | piid | valori |
|----------|------|------|--------|
| power | 2 | 1 | 1=ON, 2=OFF |
| mode | 2 | 3 | 0=AI, 1=Potente, 2=Sonno, 3=Manuale, 7=Naturale |
| fan_speed | 2 | 4 | int 1–10 |
| child_lock | 2 | 5 | 0=OFF, 1=ON |
| temperature | 3 | 2 | °C read-only |

Non identificati: (2,2) sempre 0, (6,7) sempre 1 (non è child_lock).
Invalidi: (3,1), (3,3), (6,5), (6,8) → 80001 su tutti i test.

### Aggiornamenti a codice e documentazione

- `const.py`: `MF10_PROPERTY_MAP` popolato, enum `MF10_MODE_*`, dict `MF10_MODE_OPTIONS`.
- `docs/property_map.md`: creato con tabelle property, mode, metodologia discovery, target non identificati.
- `research/snapshots/example.json`: creato redacted (did=`<REDACTED>`) per documentare shape snapshot.

### Seconda tornata discovery — oscillazione e siid 6

Espanso `MF10_PROPERTY_CANDIDATES` con siid 2 piid 6–10 e siid 6 piid 1–7 (esclusi 3,6 invalidi).

| Test | finding |
|------|---------|
| Oscillazione OFF → ON | (2,7): 0→1 → **oscillazione=(2,7)** confermato |

Valori nuovi (scan oscillazione ON, 17 property totali, 14 valide):
- (2,6)=3 in entrambi gli stati (OFF e ON) → non è il toggle; ipotesi: angolo/ampiezza oscillazione
- (2,8)=0 sempre
- (2,10)=1 sempre
- (6,1)="Europe/Rome" → timezone device (read-only sistema, non polled)
- (6,2)="" → stringa vuota (nome device non impostato?)
- (6,4)=0 sempre
- (6,7)=1 sempre (non è child_lock — quello è (2,5))

`MF10_PROPERTY_MAP` aggiornato con `oscillation: {siid:2, piid:7}`.
`docs/property_map.md` aggiornato.

## Prossimi passi

1. Runtime test del tool (utente).
2. Se necessario, fix bug emersi dal primo run.
3. Ciclo discovery: snapshot before → cambio funzione dall'app Dreamehome (uno alla volta: power, speed +/-, mode, oscillation, light, child lock, timer) → snapshot after → diff.
4. Popolare `docs/property_map.md` con le `(siid, piid)` validate.
5. Aggiornare `MF10_PROPERTY_MAP` in `const.py` con la mappa confermata.
6. Solo allora: M2-logico (coordinator) + M3-logico (fan entity).

## Advisor review #2 (post-implementazione, pre-commit)

Issue sollevate e azioni:

1. **Blocker — handler in `_scan` troppo stretto**: `tools/scan_properties.py` catturava solo `DreameApiError`. In uno scan da ~60s (300 properties × 200ms con batch-size 1) un singolo `DreameConnectionError` (timeout TCP, blip rete) avrebbe propagato fino al `ClientSession`, abortendo l'intero scan e **lasciando il JSON non scritto**. Fix: aggiunto `DreameConnectionError` alla stessa clausola except → batch marcato come errore e scan continua. Preflight invariato (lì abortire prima del full scan è OK).
2. **Task miss — `plans/README.md` non aggiornato**: la task list del piano lo richiedeva ("M4 anticipato"). Aggiunta sezione "Ordine effettivo di esecuzione" che documenta la deviazione dalla roadmap originale.
3. **Riconosciuto, non bloccante**: shape di `listV2` (`d.get("deviceInfo", {}).get("deviceName")`) è un guess — se non match, il listing stampa nomi vuoti ma non si rompe. Diagnostico, da verificare al primo run reale.
4. **Riconosciuto, già acknowledged**: semantica errori batch (envelope vs per-item) → tutto il design difensivo (`batch_size=1` default + preflight) esiste proprio per scoprirla empiricamente.

Issue rinviate con motivazione:

- Manifest URLs ancora `TODO-set-real-url-before-publishing` → non blocca M4, si aggiornano quando si pubblica su HACS.
