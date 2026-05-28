# Dreame MF10 — Home Assistant Custom Integration

## Cosa è questo progetto
Custom integration Home Assistant per il ventilatore **Dreame Bladeless Fan MF10** (`dreame.fan.u2519`).
Approccio **cloud-first** via Dreame Cloud API (credenziali Dreamehome). Nessuna API locale stabile assunta.

Spec autoritativa: [specs/prompt_coding_agent_dreame_mf_10_home_assistant.md](specs/prompt_coding_agent_dreame_mf_10_home_assistant.md).
In caso di conflitto fra CLAUDE.md e la spec, **vince la spec**.

## Dispositivo target
```
Model ID: dreame.fan.u2519
Device:   Dreame Bladeless Fan MF10
DID:      -115387050
MAC:      90:EB:48:22:90:EF
Firmware: 1035 / Plugin 104
```

## Stato attuale
**Fase 1 / Milestone 3 completata** — integrazione funzionante con le seguenti limitazioni.

Cosa funziona:

- Config flow, autenticazione cloud, polling 30s
- Fan entity: velocità (10 livelli), preset mode (ai/powerful/sleep/manual/natural), oscillazione
- Sensor: temperatura °C

Blocco aperto — **on/off**:

- `siid=2, piid=1` = power state (1=on, 2=standby) — **read-only**, non scrivibile
- Action `siid=2, aiid=1/2/3` **causano WiFi reset** sul MF10 — NON eseguire mai
- Il device in standby è connesso WiFi e risponde a tutti i comandi tranne power-on
- Candidato da testare: `siid=11, piid=5` (bool, write-only) da modelli Dreame fan simili su miot-spec.org
- Log di sessione: `sessions/2026-05-28-on-off-investigation.md`

## Fasi (incrementali, da rispettare nell'ordine)
1. **Fase 1** — Integrazione minima: login cloud → discovery → fan entity → on/off + speed 1–10. Property map provvisoria + logging.
2. **Fase 2** — Discovery property map completa via snapshot/diff dall'app Dreamehome.
3. **Fase 3** — Entità avanzate: switch (display/child lock/buzzer/oscillazione), select (mode), number (timer/angoli), button, preset modes.
4. **Fase 4** — Hardening: config flow robusto, diagnostics con redaction, options flow, HACS packaging, README, traduzioni, test.

## Architettura
```
custom_components/dreame_mf10/
  __init__.py  manifest.json  const.py
  config_flow.py  coordinator.py  dreame_cloud.py
  fan.py  sensor.py  switch.py  select.py  number.py  button.py
  diagnostics.py  strings.json  translations/{en,it}.json
tools/
  scan_properties.py   # CLI standalone per snapshot proprietà
  diff_properties.py   # diff fra due snapshot
  call_action.py       # test manuale action MiOT (solo on-demand)
```
Dominio: `DOMAIN = "dreame_mf10"`. Modello: `MODEL_MF10 = "dreame.fan.u2519"`.

## Regole non negoziabili
- **Niente blocking dell'event loop HA**: tutto async o via executor. Usare `DataUpdateCoordinator`.
- **Niente segreti nei log**: mai password, token, refresh_token, cookies, header auth. Vale anche per diagnostics.
- **Property map provvisoria != definitiva**: tenere separate `MF10_PROPERTY_CANDIDATES` (sperimentale) e `MF10_PROPERTY_MAP` (validata empiricamente). Non hardcodare prima della validazione.
- **Non esporre come stabili funzioni non verificate**: dietro flag `experimental_entities` (default off).
- **Polling**: default 30s, mai sotto 10s. Refresh immediato dopo ogni comando.
- **Action MiOT mai chiamate alla cieca all'avvio**: solo via `tools/call_action.py` esplicito. Le action possono muovere pale/spegnere/resettare.
- **Off behavior** configurabile (`real` vs `soft`/sleep speed 1). Default `real`, da rivalutare se il device va in deep standby non risvegliabile via cloud.
- **Backward compat**: prevedere `MODEL_CAPABILITIES` dict — non scrivere codice che impedisca di aggiungere altri modelli Dreame fan in futuro.

## Scope: cosa NON fare in fase 1
- Reverse engineering firmware, BLE, IR/RF, API locale non documentata. Solo cloud.
- Esporre entità avanzate prima che la property map sia validata.
- Refactoring o feature non richieste dalla fase in corso.

## Criteri "done" per la prima release utile
Utente può: vedere disponibilità, accendere, spegnere (o soft-off), impostare velocità 1–10, vedere stato aggiornarsi dopo comandi da app Dreamehome, leggere log diagnostici per continuare la mappatura.

## Workflow di sviluppo in questo repo

### Struttura cartelle di lavoro
- [specs/](specs/) — spec autoritative del progetto (input immutabile)
- [plans/](plans/) — piani di lavoro per fase/milestone (`phase1-milestone1.md`, ecc.). Un piano vivo per sessione di lavoro.
- [sessions/](sessions/) — log per sessione (`YYYY-MM-DD-topic.md`): cosa fatto, decisioni, blocchi, prossimi passi.
- [docs/](docs/) — documentazione tecnica derivata (`property_map.md`, troubleshooting, ecc.).
- [research/](research/) — output di discovery: `snapshots/` (JSON da `scan_properties.py`), `diffs/` (output `diff_properties.py`), note di reverse engineering.
- [sandbox/](sandbox/) — istanza Docker locale di Home Assistant per smoke test dell'integrazione (`docker compose -f sandbox/docker-compose.yml up -d`, poi http://localhost:8123). Vedi [sandbox/README.md](sandbox/README.md).

### Convenzioni
- Ogni nuova sessione: leggi `CLAUDE.md` + il piano attivo in `plans/` + le ultime note in `sessions/`.
- Snapshot proprietà: nome `before-<azione>.json` / `after-<azione>.json`, conservati in `research/snapshots/`.
- Mai committare credenziali Dreamehome. Usare env vars (`DREAME_USERNAME`, `DREAME_PASSWORD`). Aggiungere a `.gitignore` qualsiasi file `*.local.json` o `secrets*`.
- Repo pubblico su GitHub: **prima di committare**, verificare diff per assenza di credenziali, DID/MAC sensibili nei log di esempio (sostituire con placeholder nei docs).
- **Commit periodici e piccoli**: committare al termine di ogni unità logica completata (un milestone, un file di feature, un fix dell'advisor accorpato, ecc.). Niente mega-commit di intere sessioni. Linee guida:
  - Un commit = un cambiamento concettuale (es. "M0 scaffolding", "fix advisor M0 review", "M2 coordinator wiring"). Se serve `e` nel messaggio per descrivere il commit, è probabilmente da spezzare.
  - Mai committare WIP rotto su `main`. Se devi salvare uno stato intermedio non funzionante, usa un branch.
  - Prima di ogni commit: `git status` + `git diff` per verificare niente credenziali, niente snapshot `research/` non redacted, niente token nei log di esempio.
  - Messaggio commit: imperativo, italiano o inglese coerente nella sessione. Body opzionale solo se il "perché" non è ovvio dal diff.
  - Push su `main` solo dopo conferma esplicita dell'utente (repo pubblico).
- **Advisor gate (obbligatorio)**: ogni sessione di sviluppo deve passare per `advisor()` almeno **due volte**:
  1. **Prima** di committere a un approccio — dopo l'orientamento iniziale (lettura spec, esplorazione codice, fetch di riferimenti) ma **prima** di scrivere codice non triviale o prendere decisioni architetturali.
  2. **Prima** di dichiarare completato qualsiasi milestone — con i file già scritti su disco, così se l'advisor cade la deliverable è già durabile.
  Il session log deve citare l'output sintetico dell'advisor e cosa è stato cambiato in risposta. "Advisor ha visto" ≠ "advisor ha approvato": le issue sollevate vanno risolte o esplicitamente accettate con motivazione scritta nel log. Su task brevi e reattivi (1–2 step) l'advisor non è obbligatorio, ma resta consigliato.

### Stile di collaborazione atteso (da CLAUDE.md globale utente)
- Se il task ha più interpretazioni → elenco opzioni + conferma prima di scrivere codice.
- Definire criteri di successo prima di iniziare.
- Modificare solo file/righe del task. Niente refactoring opportunistico.
- Segnalare deviazioni dal piano prima di procedere.
- Risposte in italiano, terse, con accenti corretti.

## Riferimenti utili
- Codice ispirazionale: https://github.com/CodyJon/dreame-ap10-integration (modello diverso, property map non riusabile cieca)
- HA dev docs — Integration Quality Scale, `DataUpdateCoordinator`, `FanEntity`, `ConfigFlow`
- MiOT spec (per capire `siid`/`piid`/`aiid`): https://iot.mi.com/new/doc/accesses/direct-access/embedded-development/spec
