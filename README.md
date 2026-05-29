# Dreame MF10 — Home Assistant Custom Integration

> **Status: Phase 3 complete + on/off solved (2026-05-29).**
> Full control from Home Assistant including **power on/off** via a proper `fan` entity
> (on/off, speed, preset modes), plus switches/select/number/sensor for the rest. On/off is
> performed via the MiOT action the Dreamehome app uses (`siid=2 aiid=1`, input `piid=1` value 1/0),
> discovered by capturing the app's traffic and validated on the real device.

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
| `fan.dreame_mf10`                            | `fan`           | Main control: on/off, speed (%), preset modes (AI/Powerful/Sleep/Manual/Natural) |
| `sensor.dreame_mf10_temperature`             | `sensor`        | Ambient temperature (°C, read-only)                             |
| `switch.dreame_mf10_child_lock`              | `switch`        | Child lock                                                      |
| `switch.dreame_mf10_continuous_monitoring`   | `switch`        | TempSync / continuous temperature monitoring                    |
| `switch.dreame_mf10_key_tone`                | `switch`        | Button beep                                                     |
| `switch.dreame_mf10_display_led`             | `switch`        | LED display always-on (briefly flashes on command anyway)       |
| `switch.dreame_mf10_device_rotation`         | `switch`        | Base rotation (the whole fan rotating on itself)                |
| `select.dreame_mf10_oscillation`             | `select`        | Blade oscillation: off / left / right / both (independent/sync/staggered) |
| `number.dreame_mf10_off_timer`               | `number`        | Auto-off timer (hours, 0 = disabled)                            |

Fan speed is only honored by the device in **Manual** mode, so setting a speed (the fan
percentage slider) automatically switches the device to Manual.

## On/off (solved 2026-05-29)

Power on/off **works from Home Assistant**, via the same MiOT action the Dreamehome app uses:

- **Power on**: `action siid=2, aiid=1, in=[{piid:1, value:1}]`
- **Power off**: `action siid=2, aiid=1, in=[{piid:1, value:0}]`

`siid=2, piid=1` is only the read-only **state indicator** (1 = on, 2 = standby). The on/off
command is the action above — discovered by capturing the app's traffic with a transparent MITM
(the app talks to the cloud over an IP-based endpoint, which is why earlier hostname-based
captures missed it).

> ⚠️ The same action `aiid=1` with an **empty** input (`in=[]`) triggers a **WiFi reset** on the
> device (physical re-pairing required). The power command works only with the explicit
> `in=[{piid:1,value}]` argument. The integration hardcodes this input, so the reset payload is
> unreachable from HA.

## What does NOT work yet

- **Oscillation speed** (standard / fast) — not exposed via `get_properties`; likely sent
  as a contextual parameter with the oscillation command. Not yet replicated.
- **Real-time state via MQTT** — state still comes from 30 s polling + immediate post-command
  refresh. The device does push `properties_changed` over MQTT (`/status/...`); switching the
  coordinator to MQTT push is a planned follow-up (needs access-token refresh + reconnect handling).
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
