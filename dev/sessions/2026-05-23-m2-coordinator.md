# 2026-05-23 — M2 (logico): Coordinator + sensor temperatura

## Contesto

Terza sessione di sviluppo. M4 chiusa nella sessione precedente (push `38044e8`).
`MF10_PROPERTY_MAP` validata empiricamente con 6 property confermate.
Scope: M2 (coordinator) con aggiunta sensor temperatura (M2+ε, scelta utente) per
verifica end-to-end del pipeline senza aspettare M3 (fan entity).

## Cosa fatto

- **Advisor gate #1** (pre-codice): advisor ha confermato il design, segnalato i constraint
  critici (bindDomain, error mapping, async_get_clientsession, unload order).
- Implementati:
  - [coordinator.py](../custom_components/dreame_mf10/coordinator.py) —
    `MF10Coordinator(DataUpdateCoordinator)`: login + device list fetch per `bindDomain`,
    poll 30s su 6 property validate, error mapping corretto.
  - [__init__.py](../custom_components/dreame_mf10/__init__.py) — rewire completo:
    cloud init, login, device lookup per `bindDomain`, `async_config_entry_first_refresh`,
    `async_forward_entry_setups`, `async_unload_platforms`.
  - [sensor.py](../custom_components/dreame_mf10/sensor.py) —
    `MF10TemperatureSensor`: `SensorDeviceClass.TEMPERATURE`, `has_entity_name=True`,
    `device_info` con `identifiers + connections(MAC)`.
  - [const.py](../custom_components/dreame_mf10/const.py) — aggiunto `PLATFORMS = ["sensor"]`.
- **Advisor gate #2** (post-implementazione):
  - Tutti i constraint pre-codice verificati ✅.
  - Segnalato: aggiungere MAC a `device_info.connections` (fatto).
  - Segnalato: smoke test sandbox obbligatorio (sandbox test eseguito).
  - Segnalato: piani + sessione mancanti (questo file + plan scritti).

## Decisioni

1. **`bindDomain` ri-fetchato a ogni setup**: il config_flow non lo salva. Overhead di una
   chiamata extra accettabile vs. aggiunta di un campo in `config_flow._create_entry` (non M2).
2. **`ConfigEntryNotReady` per `DreameAuthError` in setup**: `async_step_reauth` non ancora
   implementato. Comportamento: HA riprova il setup dopo un intervallo. TODO in M4 hardening.
3. **`ConfigEntryAuthFailed` in `_async_update_data`**: HA standard per segnalare credenziali
   scadute durante il polling — marca l'entry come REAUTH_REQUIRED in UI.
4. **`has_entity_name=True` + `SensorDeviceClass.TEMPERATURE`**: auto-genera nome "Temperature"
   via device class HA, senza bisogno di `translation_key` o stringhe custom.

## Smoke test risultati

Eseguito 2026-05-23 su sandbox Docker (HA stable, porta 8123):

```
07:30:32.755 DEBUG dreame_cloud: Dreame login OK (region=eu)
07:30:32.799 DEBUG dreame_mf10: Device -115387050 bindDomain=10000.mt.eu.iot.dreame.tech:19973
07:30:33.068 DEBUG coordinator: Finished fetching dreame_mf10_-115387050 data in 0.267s (success: True)
07:30:33.072 INFO sensor: Registered new entity: sensor.dreame_mf10_temperatura
07:31:02.638 DEBUG coordinator: Finished fetching ... in 0.227s (success: True)   ← +29s
07:31:32.800 DEBUG coordinator: Finished fetching ... in 0.385s (success: True)   ← +30s
```

Tutti i criteri di successo soddisfatti: entry caricata, sensor registrata, polling 30s regolare.

## Blocchi / domande aperte

- `async_step_reauth` ancora mancante — entry può finire in REAUTH_REQUIRED senza handler.
- M3 (fan entity) — prossimo passo.

## Prossimi passi

1. Smoke test sandbox (restart HA, verificare sensor in UI).
2. Commit + push M2.
3. M3: `fan.py` con `FanEntity`.
