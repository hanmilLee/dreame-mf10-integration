# Dreame MF10 — Home Assistant Custom Integration

## Cosa è questo progetto
Custom integration Home Assistant per il ventilatore **Dreame Bladeless Fan MF10** (`dreame.fan.u2519`).
Approccio **cloud-first** via Dreame Cloud API (credenziali Dreamehome). Nessuna API locale stabile assunta.

Spec autoritativa: [dev/specs/prompt_coding_agent_dreame_mf_10_home_assistant.md](dev/specs/prompt_coding_agent_dreame_mf_10_home_assistant.md).
In caso di conflitto fra CLAUDE.md e la spec, **vince la spec**.

## Dispositivo target
```
Model ID: dreame.fan.u2519
Device:   Dreame Bladeless Fan MF10
DID:      <DID>
MAC:      <MAC>
Firmware: 1035 / Plugin 104
```

## Stato attuale
**Fase 1 / Milestone 3 completata + Fase 2 (discovery) completata + Fase 3 (entità avanzate) completata**.

Property map validata empiricamente: 13 property utilizzabili, mappate via before/after diff
con app Dreamehome. Vedi [docs/property_map.md](docs/property_map.md) e
[dev/sessions/2026-05-28-property-discovery.md](dev/sessions/2026-05-28-property-discovery.md).

Cosa funziona (entità HA esposte):

- **fan**: entità principale — **on/off**, velocità (percentuale 1–10), preset mode
  (AI/Potente/Sonno/Manuale/Naturale). Velocità applicata forzando mode=manual (il device
  onora `fan_speed` solo in manuale). Stato ottimistico fino a conferma del poll.
- **sensor**: temperatura ambientale (°C)
- **switch**: blocco bambini, monitoraggio continuo, tono tasti, display LED, rotazione device
- **select**: oscillazione pale (6 stati coerenti: off/left/right/both[independent|sync|staggered])
- **number**: timer spegnimento (0–12 ore)
- Config flow, autenticazione cloud, polling 30s, refresh immediato post-comando

**ON/OFF RISOLTO (2026-05-29)** — power controllabile via action MiOT:

- **POWER ON**: `action siid=2, aiid=1, in=[{piid:1, value:1}]`
- **POWER OFF**: `action siid=2, aiid=1, in=[{piid:1, value:0}]`
- Scoperto via cattura MITM (mitmproxy WireGuard) dell'app, validato sul device reale e in HA.
- `siid=2, piid=1` resta read-only: è solo l'**indicatore** di stato (1=on, 2=standby), letto dal coordinator.
- ⚠️ **L'action aiid=1 con params VUOTI `[]` resetta il WiFi**. Il power funziona SOLO con
  l'argomento `in=[{piid:1,value}]`. `coordinator.async_set_power` hardcoda i params → reset
  irraggiungibile dall'integrazione. `dev/tools/call_action.py` ha una guardia anti-reset.
- La conclusione precedente "on/off impossibile / MQTT" era ERRATA (l'app usa REST su endpoint
  IP-based, mancato dalle catture per-hostname). Vedi [dev/sessions/2026-05-29-mqtt-proxyman-investigation.md].

Property non rilevabili / pericolose:

- Velocità oscillazione pale (standard/rapido): non rilevabile via `get_properties` —
  probabilmente parametro contestuale nel comando oscillazione
- `(4,2)`: write con `value=90` bypassa `(2,4)` e imposta motore in scala raw
  (mostrato "speed 13"). Non usare nell'integrazione.

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
  fan.py  sensor.py  switch.py  select.py  number.py
  strings.json  translations/{en,it}.json
dev/tools/
  scan_properties.py   # CLI standalone per snapshot proprietà
  diff_properties.py   # diff fra due snapshot
  call_action.py       # test manuale action MiOT (solo on-demand)
```
Dominio: `DOMAIN = "dreame_mf10"`. Modello: `MODEL_MF10 = "dreame.fan.u2519"`.

`fan.py` espone la `FanEntity` (on/off + velocità + preset). Il vecchio vincolo "niente fan.py
perché on/off non supportabile" è **obsoleto** dal 2026-05-29: il comando power (action 2/1) è
noto e validato. Le altre primitive (switch/select/number) restano granulari per il controllo fine.

## Regole non negoziabili
- **Niente blocking dell'event loop HA**: tutto async o via executor. Usare `DataUpdateCoordinator`.
- **Niente segreti nei log**: mai password, token, refresh_token, cookies, header auth. Vale anche per diagnostics.
- **Property map provvisoria != definitiva**: tenere separate `MF10_PROPERTY_CANDIDATES` (sperimentale) e `MF10_PROPERTY_MAP` (validata empiricamente). Non hardcodare prima della validazione.
- **Non esporre come stabili funzioni non verificate**: dietro flag `experimental_entities` (default off).
- **Polling**: default 30s, mai sotto 10s. Refresh immediato dopo ogni comando.
- **Action MiOT mai chiamate alla cieca all'avvio**: solo via `dev/tools/call_action.py` esplicito. Le action possono muovere pale/spegnere/resettare.
- **Power = action 2/1 con input obbligatorio**: on/off via `action siid=2 aiid=1 in=[{piid:1,value:1|0}]`.
  ⚠️ La stessa action con `in` VUOTO resetta il WiFi. Usare sempre `coordinator.async_set_power`
  (params hardcoded) — mai costruire l'action power a mano.
- **Backward compat**: prevedere `MODEL_CAPABILITIES` dict — non scrivere codice che impedisca di aggiungere altri modelli Dreame fan in futuro.

## Scope: cosa NON fare in fase 1
- Reverse engineering firmware, BLE, IR/RF, API locale non documentata. Solo cloud.
- Esporre entità avanzate prima che la property map sia validata.
- Refactoring o feature non richieste dalla fase in corso.

## Criteri "done" per la prima release utile
Utente può: vedere disponibilità, accendere, spegnere (o soft-off), impostare velocità 1–10, vedere stato aggiornarsi dopo comandi da app Dreamehome, leggere log diagnostici per continuare la mappatura.

## Workflow di sviluppo in questo repo

### Struttura cartelle di lavoro
- [dev/specs/](dev/specs/) — spec autoritative del progetto (input immutabile)
- [dev/plans/](dev/plans/) — piani di lavoro per fase/milestone (`phase1-milestone1.md`, ecc.). Un piano vivo per sessione di lavoro.
- [dev/sessions/](dev/sessions/) — log per sessione (`YYYY-MM-DD-topic.md`): cosa fatto, decisioni, blocchi, prossimi passi.
- [docs/](docs/) — documentazione tecnica derivata (`property_map.md`, troubleshooting, ecc.).
- [dev/research/](dev/research/) — output di discovery: `snapshots/` (JSON da `scan_properties.py`), `diffs/` (output `diff_properties.py`), note di reverse engineering.
- [sandbox/](sandbox/) — istanza Docker locale di Home Assistant per smoke test dell'integrazione (`docker compose -f sandbox/docker-compose.yml up -d`, poi http://localhost:8123). Vedi [sandbox/README.md](sandbox/README.md).

### Convenzioni
- Ogni nuova sessione: leggi `CLAUDE.md` + il piano attivo in `dev/plans/` + le ultime note in `dev/sessions/`.
- Snapshot proprietà: nome `before-<azione>.json` / `after-<azione>.json`, conservati in `dev/research/snapshots/`.
- Mai committare credenziali Dreamehome. Usare env vars (`DREAME_USERNAME`, `DREAME_PASSWORD`). Aggiungere a `.gitignore` qualsiasi file `*.local.json` o `secrets*`.
- Repo pubblico su GitHub: **prima di committare**, verificare diff per assenza di credenziali, DID/MAC sensibili nei log di esempio (sostituire con placeholder nei docs).
- **Commit periodici e piccoli**: committare al termine di ogni unità logica completata (un milestone, un file di feature, un fix dell'advisor accorpato, ecc.). Niente mega-commit di intere sessioni. Linee guida:
  - Un commit = un cambiamento concettuale (es. "M0 scaffolding", "fix advisor M0 review", "M2 coordinator wiring"). Se serve `e` nel messaggio per descrivere il commit, è probabilmente da spezzare.
  - Mai committare WIP rotto su `main`. Se devi salvare uno stato intermedio non funzionante, usa un branch.
  - Prima di ogni commit: `git status` + `git diff` per verificare niente credenziali, niente snapshot `dev/research/` non redacted, niente token nei log di esempio.
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
