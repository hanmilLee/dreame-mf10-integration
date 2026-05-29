# Phase 1 — Milestone 4: Discovery tools (eseguito fuori ordine)

## Status: DONE 2026-05-22

Property map validata empiricamente: power (2,1), mode (2,3), fan_speed (2,4), child_lock (2,5),
temperature (3,2). Modalità: 0=AI, 1=Potente, 2=Sonno, 3=Manuale, 7=Naturale.
`MF10_PROPERTY_MAP` in `const.py` popolato. `docs/property_map.md` scritto.
Bug trovati e fixati durante runtime: bindDomain routing (404 senza), candidates-only mode
(brute-force impraticabile per latenza 8s/request su property sconosciute).

- `tools/scan_properties.py` + `tools/diff_properties.py` + `tools/README.md` scritti.
- `diff_properties.py` smoke testato con snapshot sintetici (cambi rilevati, modalità testo + JSON OK).
- `scan_properties.py` validato a livello sintassi (`py_compile` OK). Runtime test richiede `aiohttp` installato + credenziali → delegato all'utente alla prima sessione di discovery reale.
- `example.json` redacted differito al primo scan reale (per redactare una shape effettiva, non ipotetica).

## Nota su ordine roadmap
La roadmap originale (vedi `plans/README.md`) era M2 Polling → M3 Fan → M4 Tool discovery.
**Decisione utente 2026-05-22**: invertire e fare prima M4. Razionale:
- `MF10_PROPERTY_CANDIDATES` in `const.py` sono guess non validati (siid 2 power/mode/speed, siid 3 temp, siid 6 lock — pattern AP10).
- Costruire coordinator + fan entity su candidate sbagliati = rumore in HA + entity rotte. Validare la mappa offline via CLI è più rapido (no riavvio HA, no UI).
- Lo snapshot JSON prodotto serve anche come documentazione della mappa quando si scriverà `docs/property_map.md`.

## Obiettivo
CLI standalone (`tools/scan_properties.py`, `tools/diff_properties.py`) per:
1. Interrogare TUTTE le combinazioni `(siid, piid)` in un range configurabile sul MF10 via Dreame Cloud.
2. Salvare lo snapshot in `research/snapshots/`.
3. Confrontare due snapshot per identificare quale `(siid, piid)` cambia quando l'utente modifica una specifica funzione dall'app Dreamehome (workflow before/after).

## Criteri di successo
1. `tools/scan_properties.py` eseguibile da repo root:
   - Credenziali da **env vars** `DREAME_USERNAME` / `DREAME_PASSWORD` (mai da argv → no shell history leak).
   - Argomenti CLI: `--region` (default `eu`), `--did` (opzionale; se omesso elenca i devices e abortisce), `--siid-min/max` (default 1..10), `--piid-min/max` (default 1..30), `--output PATH` (opzionale), `--label SLUG` (**obbligatorio**, es. `before-speed-change`), `--batch-size` (default **1**, vedi rischio batch sotto).
   - Output JSON in `research/snapshots/<YYYY-MM-DD-HHMMSS>-<label>.json` (default) con shape:
     ```json
     {
       "metadata": { "model": "...", "did": "...", "region": "...", "timestamp_utc": "...", "scan_params": {...} },
       "results": [ { "siid": 2, "piid": 1, "code": 0, "value": true }, { "siid": 9, "piid": 7, "code": -704042011 }, ... ]
     }
     ```
2. **Tolleranza errori per-property**: una `piid` invalida (code != 0) non aborta; viene loggata nel JSON con `code` (e `error` testuale opzionale). Lo scan continua.
   - **Aperto empiricamente**: non sappiamo se Dreame ritorna (a) envelope `code=0` + errori per-item nel result list (semantica MiOT standard), oppure (b) envelope `code != 0` rifiutando l'intero batch. Per questo `--batch-size` default = **1** → ogni property è isolata. Al primo run reale si verifica e si può alzare.
   - **Pre-flight check**: prima del full scan, una singola `get_properties` su candidate noto (`siid=2, piid=1` = power per pattern MiOT comune). Se shape della response inaspettata → stop con errore esplicativo, no full scan.
3. **Redaction**: token, refresh_token, headers di auth MAI nel JSON. Solo `did` (che è già pubblico nel binding utente, ma marcabile redacted con `--redact-did` opzionale).
4. **Rate limiting soft**: pausa di 200ms fra batch per non triggerare ban lato Dreame.
5. `tools/diff_properties.py before.json after.json`:
   - Mostra solo le `(siid, piid)` con `value` cambiato fra i due snapshot.
   - Ignora property con code != 0 in entrambi.
   - Output testo leggibile su stdout; flag `--json` per output strutturato.
6. `tools/README.md` con: requisiti env, esempio di run, workflow before/after, troubleshooting.
7. `research/snapshots/example.json` committato (redacted, did/MAC sostituiti) per illustrare il formato. **Differito**: si scrive DOPO il primo scan reale, così la redaction si applica a una shape effettiva e non a una ipotetica.
8. Nessuna nuova dipendenza pip oltre a `aiohttp` (già usata da `dreame_cloud.py`).

## Task list
- [ ] `tools/scan_properties.py` (eseguito come `python tools/scan_properties.py …` da repo root; NO `tools/__init__.py` per evitare ambiguità import):
  - [ ] Argparse + lettura env vars
  - [ ] `sys.path` manipulation per importare `custom_components.dreame_mf10.dreame_cloud`
  - [ ] `aiohttp.ClientSession` + reuse di `DreameCloud`
  - [ ] Device listing quando `--did` manca (stampa `did` + model, MAC nascosto di default — solo con `-v`)
  - [ ] **Pre-flight**: una singola `get_properties` su `(2,1)` per validare la shape della response
  - [ ] Scan loop con `--batch-size` (default 1) + sleep 200ms fra request
  - [ ] Serializzazione JSON con metadata + results (lista flat, ordinata per siid,piid)
- [ ] `tools/diff_properties.py`:
  - [ ] Carica 2 snapshot, valida shape
  - [ ] Diff `(siid, piid) → value` solo se entrambi `code == 0` e value diverso
  - [ ] Output testo: `siid=X piid=Y : <before> → <after>`
- [ ] `tools/README.md` (workflow + esempi)
- [ ] `research/snapshots/example.json` redacted — **differito**: scritto solo DOPO il primo scan reale, per garantire che la redaction copra la shape effettiva (no campi sorpresa).
- [ ] `sessions/2026-05-22-m4-discovery-tools.md` log sessione
- [ ] Aggiornare `plans/README.md` roadmap con nota "M4 anticipato"

## Fuori scope (esplicito)
- Coordinator (`coordinator.py`) — milestone successiva (era M2, ora M5 logico).
- Fan entity — successiva.
- `tools/call_action.py` (invocare action MiOT) — pericoloso, separato.
- Auto-promozione di `MF10_PROPERTY_CANDIDATES` → `MF10_PROPERTY_MAP`: la mappa va riempita **a mano** dopo aver guardato i diff. Niente magia auto-inferenziale.
- Modificare `const.py` in questa sessione: si fa dopo aver osservato i risultati dello scan reale.
- `tools/call_action.py`: invocare action MiOT (può muovere pale / spegnere device). Va separato in commit dedicato con safeguards (confirm prompt, `--yes` flag). Non in questa milestone.

## Rischi / assunzioni
- **Assunzione**: range default `siid 1..10, piid 1..30` (300 query, 30 batch da 10) copre tutto ciò che un fan MiOT espone. AP10 va fino a siid 6 — un margine fino a 10 è prudente.
- **Assunzione**: `get_properties` con `(siid, piid)` inesistente ritorna code di errore documentato MiOT (es. `-704042011 unreachable property`) e NON solleva eccezione HTTP. Da verificare nei primi run.
- **Rischio basso — rate limiting**: con 30 batch ×200ms ≈ 6s totali. Improbabile triggeri abuse detection. Se accade, alzare pausa.
- **Rischio medio — ghost properties**: alcune piid potrebbero ritornare `code=0` con `value=None` o default — questi NON sono proprietà reali. Da non promuovere nella mappa senza un diff before/after che le faccia cambiare.
- **Sicurezza repo pubblico**: snapshot reali NON committati (`.gitignore` già esclude `research/snapshots/*.json` tranne `example.json`). Verificare il diff prima del commit.

## Domande aperte
1. **`tools/` viene eseguito dal repo root o serve installazione del package?** Proposta: `python tools/scan_properties.py ...` da repo root, con sys.path.append per importare `custom_components.dreame_mf10.dreame_cloud`. Pulito ma non pip-installable. OK per uso interno.
2. **Logging**: solo print su stdout/stderr? O usare logging stdlib con `-v` flag? Proposta: logging stdlib, default INFO, `-v` per DEBUG.
3. **Esempio redacted committato**: necessario? Pro: utile per nuovi contributors. Contro: piccolo overhead di manutenzione. Proposta: sì, minimal (~5 entries).

## Prossima milestone
M5-logico (era M2) — Coordinator + property polling, usando la mappa validata via questo tool.
