# Phase 1 — Milestone 2 (logico): Coordinator + Sensor temperatura

## Status: DONE 2026-05-23

Coordinator wired, polling 30s, sensor temperatura visibile in HA UI.

## Obiettivo

Implementare `coordinator.py` con `DataUpdateCoordinator` che polliga le 6 property
validate di `MF10_PROPERTY_MAP` ogni 30s via `DreameCloud.async_get_properties`.
Aggiungere `sensor.dreame_mf10_temperature` per verifica end-to-end del pipeline.

## Criteri di successo

1. Config entry si carica senza errori (no banner rosso in HA UI).
2. `sensor.dreame_mf10_temperature` appare in Developer Tools → States con valore numerico.
3. Il polling ogni 30s è visibile dai log DEBUG (`dreame_mf10_<did>`).
4. Unload pulito: nessun residuo in `hass.data[DOMAIN]`.

## Decisioni

- **Scope M2+ε (su richiesta utente)**: coordinator + sensor temperatura anziché solo coordinator.
  Razionale: verifica end-to-end visibile in UI senza aspettare M3 (fan entity).
- **`bindDomain` non in config entry**: il config_flow non lo salva. Il coordinator lo ri-fetcha
  dalla device list a ogni `async_setup_entry`. Overhead trascurabile (una chiamata extra al login).
- **`DreameAuthError` in setup → `ConfigEntryNotReady`**: `async_step_reauth` non ancora
  implementato (deferred da M0 advisor). Si usa `ConfigEntryNotReady` per evitare un loop di
  reauth vuoto. In `_async_update_data` invece si usa `ConfigEntryAuthFailed` (standard HA).
- **MAC in `device_info.connections`**: migliora matching nel device registry HA quando altri
  integration scoprono lo stesso device. MAC presente in `entry.data["mac"]`.

## Task list

- [x] `coordinator.py` — `MF10Coordinator(DataUpdateCoordinator)`
- [x] `const.py` — aggiunto `PLATFORMS = ["sensor"]`
- [x] `__init__.py` — rewire `async_setup_entry` + `async_unload_entry`
- [x] `sensor.py` — `MF10TemperatureSensor(CoordinatorEntity, SensorEntity)`
- [x] Advisor gate #1 (pre-codice) + #2 (post-implementazione)
- [x] Smoke test sandbox (riavvio HA, verificare sensor in UI)
- [x] `plans/phase1-milestone2-coordinator.md` (questo file)
- [x] `sessions/2026-05-23-m2-coordinator.md`

## Fuori scope

- `async_step_reauth` in `config_flow.py` — deferred a M4 hardening.
- Fan entity (`fan.py`) — milestone successiva (M3 logico).
- Options flow — M4 hardening.
- Switch/select/number/button entity — fase 3.

## Prossima milestone

M3-logico: `fan.py` con `FanEntity` — on/off, speed 1–10, mode select, oscillation.
