# Phase 1 — Milestone 0: Setup repo

## Status: IN PROGRESS — code complete, pending HA smoke test (2026-05-22)

**Scope creep dichiarato**: in fase di esecuzione, su scelta esplicita dell'utente, lo scope di M0 è stato esteso a includere la validazione cloud reale nel config flow (originariamente assegnata a M1). Quindi `dreame_cloud.py` async è stato implementato ora invece che in M1. La sezione "Fuori scope" sottostante riflette il piano originale e non è più accurata — il client cloud E il config flow validante sono **dentro** scope effettivo di M0.

**Cosa manca per chiudere M0**:
1. Smoke test dell'utente in Home Assistant (copy → restart → add integration → login).
2. Conferma che la regione scelta funzioni con l'endpoint Dreame.

## Obiettivo
Creare scheletro installabile della custom integration `dreame_mf10` in Home Assistant, **senza ancora logica funzionante**: solo struttura file, manifest, dominio, config flow placeholder, README iniziale. Deve caricare in HA senza errori (anche se non fa nulla).

## Criteri di successo
1. La cartella `custom_components/dreame_mf10/` esiste con: `__init__.py`, `manifest.json`, `const.py`, `config_flow.py`, `strings.json`, `translations/{en,it}.json`.
2. `manifest.json` valido per HA (domain, name, version, codeowners, iot_class, requirements vuoto o minimo, config_flow=true).
3. `__init__.py` espone `async_setup_entry` / `async_unload_entry` placeholder che ritornano True senza errori.
4. `config_flow.py` ha una classe `ConfigFlow` registrata su `DOMAIN` con un solo step che accetta `username/password/region` e crea l'entry (placeholder — nessuna validazione cloud ancora).
5. `const.py` contiene le costanti già definite nella spec (`DOMAIN`, `MODEL_MF10`, `SUPPORTED_MODELS`, regioni, default polling, off behavior).
6. `README.md` root con: titolo, status (`work in progress — Phase 1 Milestone 0`), modello supportato, link a `specs/`, disclaimer reverse engineering, installazione manuale provvisoria.
7. Copiando la cartella in `<HA_config>/custom_components/` e riavviando HA, l'integrazione compare in "Add Integration", il config flow si apre, si possono inserire credenziali, viene creata una entry (anche se inerte).
8. Nessun log di errore in HA all'avvio dell'integrazione.

## Task list
- [ ] `custom_components/dreame_mf10/manifest.json`
- [ ] `custom_components/dreame_mf10/const.py` (costanti dalla spec, sezione FASE 4 → pseudocodice `const.py`)
- [ ] `custom_components/dreame_mf10/__init__.py` (async_setup_entry placeholder, niente platform forwarding ancora)
- [ ] `custom_components/dreame_mf10/config_flow.py` (single-step user con username/password/region; nessuna validazione real)
- [ ] `custom_components/dreame_mf10/strings.json` + `translations/en.json` + `translations/it.json` (label per il config flow)
- [ ] `README.md` root (status WIP, install, disclaimer)
- [ ] Smoke test mentale rileggendo i file (non c'è HA installato in questo repo)
- [ ] `sessions/<oggi>-bootstrap-m0.md` log della sessione

## Fuori scope (esplicito)
- Client `dreame_cloud.py` — Milestone 1.
- Coordinator — Milestone 2.
- Fan entity — Milestone 3.
- Tool CLI `scan_properties.py` / `diff_properties.py` — Milestone 4.
- Qualsiasi chiamata HTTP reale.
- Options flow, diagnostics, sensor/switch/select — fasi successive.

## Rischi / assunzioni
- **Assunzione**: il config flow placeholder non valida nulla — l'utente può inserire qualsiasi cosa e l'entry viene creata vuota. Va bene per M0, ma da segnalare nel README come comportamento temporaneo.
- **Assunzione**: `iot_class = "cloud_polling"` (spec dice cloud-first + polling 30s).
- **Assunzione**: `version` manifest parte da `0.1.0` (pre-release).
- **Assunzione**: `codeowners` = `["@<utente-github>"]` — chiedere user handle se serve. Per ora placeholder `["@maurosalvo"]` da confermare.
- **Rischio basso**: senza HA installato localmente non posso testare runtime. Mitigazione: codice minimale, conforme a esempi ufficiali HA, smoke test reale a carico utente.

## Domande aperte (da chiarire prima di scrivere)
1. **GitHub handle / codeowners**: confermare lo username GitHub del repo per `manifest.json`. (Default: `@maurosalvo`?)
2. **Repository URL / issue tracker** per il manifest (`documentation`, `issue_tracker`): URL del repo pubblico? (Posso lasciare placeholder e tu lo aggiorni.)
3. **Lingua UI primary**: la spec menziona `translations/{en,it}.json`. Lingua primaria del config flow = inglese (HA default) con traduzione italiana. OK?

## Prossima milestone dopo OK
M1 — Cloud login + discovery: scrivere `dreame_cloud.py` (adattando il client di [CodyJon/dreame-ap10-integration](https://github.com/CodyJon/dreame-ap10-integration)) e collegarlo al config flow per validazione vera.
