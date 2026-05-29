# Phase 1 — Milestone 3 (logico): Fan Entity

## Status: IN PROGRESS 2026-05-23

Fan entity implementata. Smoke test funzionale (test fisico su device) pendente — richiede interazione utente.

## Obiettivo

Implementare `fan.py` con `MF10FanEntity(CoordinatorEntity, FanEntity)`:

- On/off tramite MiOT power (siid=2, piid=1: 1=ON, 2=OFF)
- Speed 1–10 mappata su percentuali HA (0–100%)
- Preset modes: ai / powerful / sleep / manual / natural (siid=2, piid=3)
- Oscillation toggle (siid=2, piid=7: 0/1)
- Refresh immediato post-comando via `async_request_refresh()`

## Criteri di successo

1. `fan.dreame_mf10` appare in Developer Tools → States con stato ON/OFF e percentuale.
2. On/off via UI HA → device risponde fisicamente.
3. Cambio speed da UI → slider si aggiorna e device cambia velocità.
4. Cambio preset mode → device cambia modalità.
5. Toggle oscillazione → device avvia/ferma rotazione.
6. Temperatura sensor ancora visibile e polling regolare (no regressioni M2).

## Decisioni

- **`_attr_name = None`**: primary entity prende nome del device ("Dreame MF10").
- **`_attr_speed_count = 10`**: slider UI con 10 step discreti.
- **`FanEntityFeature.TURN_ON | TURN_OFF`**: richiesto da HA ≥ 2024.2.
- **`set_percentage(0)` → `turn_off()`**: comportamento standard HA.
- **`turn_on` batch**: power + speed/mode in un'unica chiamata `set_properties` se entrambi forniti.
- **`_prop()` helper**: usa `MF10_PROPERTY_MAP` per costruire payload, no siid/piid hardcodati in fan.py.
- **OFF_BEHAVIOR_SOFT deferred**: `turn_off` usa sempre `power=2`. Soft-off (speed=1 + sleep) rimandato a M4 hardening.
- **`async_step_reauth` ancora mancante**: `ConfigEntryAuthFailed` in `async_set_properties` segnalerà REAUTH_REQUIRED in UI.

## Task list

- [x] `coordinator.py` — aggiunto `async_set_properties` con error mapping
- [x] `const.py` — aggiunti `MF10_POWER_ON`, `MF10_POWER_OFF`, `MF10_MODE_NAME_TO_VALUE`; `PLATFORMS` aggiornato a `["sensor", "fan"]`
- [x] `fan.py` — `MF10FanEntity` completa
- [x] `README.md` — aggiornato con stato M3 ed entity table
- [x] `plans/phase1-milestone3-fan.md` (questo file)
- [ ] `sessions/2026-05-23-m3-fan.md`
- [ ] Advisor gate #2 (post-implementazione)
- [ ] Smoke test sandbox (py_compile + test funzionale su device reale)
- [ ] Commit M3

## Fuori scope

- `async_step_reauth` — deferred a M4 hardening.
- OFF_BEHAVIOR_SOFT — deferred a M4 hardening.
- Options flow — M4 hardening.
- Entità avanzate (child lock, display, buzzer, angolo, timer) — Fase 3.

## Prossima milestone

M4-hardening: `async_step_reauth`, options flow, diagnostics, OFF_BEHAVIOR_SOFT.
