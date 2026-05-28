# Dreame MF10 — Home Assistant Custom Integration

> **Status: Phase 1 / Milestone 3 — Active development, on/off control under investigation**
> Speed, preset modes, oscillation, and temperature sensor work. On/off via HA is **not yet working** — the power property is read-only and the toggle action for this model has not been identified yet. The device can be controlled (speed, mode) while running; use the physical button or the Dreamehome app to power it on/off for now.

Custom Home Assistant integration for the **Dreame Bladeless Fan MF10** (`dreame.fan.u2519`).
Cloud-first via the Dreamehome API. No local API is assumed.

## Supported devices

| Model ID            | Name                       |
|---------------------|----------------------------|
| `dreame.fan.u2519`  | Dreame Bladeless Fan MF10  |

Other Dreame fan models are out of scope for now, though the architecture
is designed to support more via a model-capability map later.

## What works today (M3)

- Config flow from the UI: sign in with Dreamehome credentials + region.
- Real authentication against the Dreame Cloud (no placeholder).
- Discovery: only accounts containing `dreame.fan.u2519` succeed.
- **Fan entity** (`fan.dreame_mf10`):
  - Speed control: 10 levels mapped to HA percentages (10 %–100 %)
  - Preset modes: `ai`, `powerful`, `sleep`, `manual`, `natural`
  - Oscillation toggle
  - ⚠️ Turn on / turn off: **not working** (see Off behavior below)
- **Temperature sensor** (`sensor.dreame_mf10_temperatura`): reads ambient °C.
- Polling every 30 s; state refreshes immediately after every command.

## Entities

| Entity                           | Domain   | Description                                         |
|----------------------------------|----------|-----------------------------------------------------|
| `fan.dreame_mf10`                | `fan`    | Main fan control (on/off, speed, mode, oscillation) |
| `sensor.dreame_mf10_temperatura` | `sensor` | Ambient temperature (°C, read-only)                 |

## On/off status (under investigation)

On/off control is the main open problem. Here is what has been established so far:

- `siid=2, piid=1` is the **power state indicator** (1 = on, 2 = standby). It is
  **read-only** — writing it returns error 80001 regardless of device state.
- Actions `siid=2, aiid=1/2/3` all cause a **WiFi reset** on this device model,
  requiring physical re-pairing. Do not call them. (Note: `aiid=3` is the toggle-power
  action on the Dreame PM10 air purifier — it maps to something completely different
  on the MF10 fan.)
- When in **standby** (power=2), the device is connected to WiFi and receives all
  cloud commands (speed, mode, oscillation — confirmed by physical beep). Only
  the power-on command does not work.
- **Next candidate**: `siid=11, piid=5` (bool, write-only, "on-off") found on
  structurally similar Dreame fan models in miot-spec.org. Not yet tested on MF10.

Use the **physical button** or the **Dreamehome app** to power the device on/off
in the meantime. All other controls work from HA once the device is running.

## What does NOT work yet

- **Turn on / turn off** — the power property is read-only; the correct toggle
  action for this model is still under investigation (see On/off status above).
  Use the physical button or the Dreamehome app in the meantime.
- `async_step_reauth` — if credentials expire while HA is running, the entry is
  marked REAUTH\_REQUIRED but no re-authentication UI is shown. Workaround: remove
  and re-add the integration.
- Options flow — polling interval and off-behavior are not configurable in the UI yet.
- Advanced entities (child lock switch, display switch, buzzer, angle, timer) — Phase 3.

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
