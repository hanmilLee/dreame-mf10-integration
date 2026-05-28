# Dreame MF10 — Home Assistant Custom Integration

> **Status: Phase 3 complete — full property map validated, all controls exposed as primitives.**
> Every control surface available in the Dreamehome app is exposed as a Home Assistant entity
> (switch / select / number / sensor), except for **on/off**, which is read-only on this model
> via the Dreame cloud API. Use the physical button or the Dreamehome app to power the device
> on/off; everything else (speed, mode, oscillation, timer, display, beep, etc.) works from HA.

Custom Home Assistant integration for the **Dreame Bladeless Fan MF10** (`dreame.fan.u2519`).
Cloud-first via the Dreamehome API. No local API is assumed.

## Supported devices

| Model ID            | Name                       |
|---------------------|----------------------------|
| `dreame.fan.u2519`  | Dreame Bladeless Fan MF10  |

Other Dreame fan models are out of scope for now, though the architecture
is designed to support more via a model-capability map later.

## What works today

- Config flow from the UI: sign in with Dreamehome credentials + region.
- Real authentication against the Dreame Cloud.
- Discovery: only accounts containing `dreame.fan.u2519` succeed.
- Polling every 30 s; state refreshes immediately after every command.

## Entities

| Entity                                       | Domain          | Description                                                     |
|----------------------------------------------|-----------------|-----------------------------------------------------------------|
| `sensor.dreame_mf10_temperature`             | `sensor`        | Ambient temperature (°C, read-only)                             |
| `binary_sensor.dreame_mf10_power_state`      | `binary_sensor` | Power state (read-only — on/off not controllable via API)       |
| `switch.dreame_mf10_child_lock`              | `switch`        | Child lock                                                      |
| `switch.dreame_mf10_continuous_monitoring`   | `switch`        | TempSync / continuous temperature monitoring                    |
| `switch.dreame_mf10_key_tone`                | `switch`        | Button beep                                                     |
| `switch.dreame_mf10_display_led`             | `switch`        | LED display always-on (briefly flashes on command anyway)       |
| `switch.dreame_mf10_device_rotation`         | `switch`        | Base rotation (the whole fan rotating on itself)                |
| `select.dreame_mf10_oscillation`             | `select`        | Blade oscillation: off / left / right / both (independent/sync/staggered) |
| `select.dreame_mf10_mode`                    | `select`        | Mode: AI / Powerful / Sleep / Manual / Natural                  |
| `number.dreame_mf10_speed`                   | `number`        | Fan speed (1–10)                                                |
| `number.dreame_mf10_off_timer`               | `number`        | Auto-off timer (hours, 0 = disabled)                            |

## On/off status (definitively confirmed)

On/off control is **not possible via the Dreame cloud API** on the MF10. After extensive
testing the conclusion is final:

- `siid=2, piid=1` is the **power state indicator** (1 = on, 2 = standby). It is
  **read-only** — writing it returns error 80001 in any device state (standby or on).
- Actions `siid=2, aiid=1/2/3` all cause a **WiFi reset** on this device model,
  requiring physical re-pairing. Do not call them. (Note: `aiid=3` is the toggle-power
  action on the Dreame PM10 air purifier — it maps to something completely different
  on the MF10 fan.)
- Probing `siid=11–20` (50 properties): all return 80001 — no hidden on/off endpoint.
- When in **standby**, the device stays on WiFi and accepts every other command
  (speed, mode, oscillation, etc.). Only on/off is unreachable from the cloud relay.
- The Dreamehome app likely uses **MQTT directly** for on/off, bypassing the REST relay
  this integration uses. Replicating that is out of scope for now.

Use the **physical button** or the **Dreamehome app** to power the device on/off.
All other controls work fine from HA, whether the device is on or in standby.

## What does NOT work yet

- **Turn on / turn off** — power is read-only via cloud (see On/off status above).
- **Oscillation speed** (standard / fast) — not exposed via `get_properties`; likely sent
  as a contextual parameter with the oscillation command. Not yet replicated.
- `async_step_reauth` — if credentials expire while HA is running, the entry is
  marked REAUTH\_REQUIRED but no re-authentication UI is shown. Workaround: remove
  and re-add the integration.
- Options flow — polling interval is not configurable in the UI yet.
- HACS packaging.

## Installation (manual, while pre-HACS)

1. Copy the folder `custom_components/dreame_mf10/` into your Home Assistant
   config: `<config>/custom_components/dreame_mf10/`.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration**, search for
   **Dreame MF10**.
4. Enter your Dreamehome **email**, **password**, and **region** (`eu`,
   `cn`, `us`, `sg`, `ru`). EU is the default for European accounts.

## Region

The Dreame cloud is sharded by region. Endpoint pattern:

```text
https://{region}.iot.dreame.tech:13267
```

If login keeps failing with `cannot_connect`, try a different region —
the app sometimes routes accounts differently than expected.

## Security

- Passwords are MD5-salted before being sent (matching the Dreamehome iOS
  app behavior); they are not stored in plaintext beyond the Home Assistant
  config entry encryption.
- Access tokens and refresh tokens live in memory only.
- Nothing sensitive (passwords, tokens, headers) is ever logged.

## Repository layout

```text
custom_components/dreame_mf10/   # the integration itself
specs/                           # authoritative project spec
plans/                           # per-milestone implementation plans
sessions/                        # development session logs
docs/                            # verified technical docs (property map, etc.)
research/                        # property scan snapshots & diffs (gitignored)
sandbox/                         # Docker-based HA instance for smoke testing
tools/                           # standalone CLI tools (scan_properties, diff_properties)
```

## MiOT property map

The full validated property map for `dreame.fan.u2519` is in
[docs/property_map.md](docs/property_map.md). Discovery was performed via
before/after differential scanning using `tools/scan_properties.py` and
`tools/diff_properties.py`.

## Credits

The Dreame Cloud auth and command flow is adapted from
[CodyJon/dreame-ap10-integration](https://github.com/CodyJon/dreame-ap10-integration)
(originally a sync `requests` implementation; here ported to async
`aiohttp` for native HA compatibility). MiOT property mapping for the
MF10 is **not** reused from AP10 — it was independently discovered via
live differential scanning on the real device.

## License

TBD. The project is currently a personal work in progress.
