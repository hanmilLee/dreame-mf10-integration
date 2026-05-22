# Dreame MF10 — Home Assistant Custom Integration

> **Status: work in progress — Phase 1 / Milestone 0**
> Login + device discovery via Dreame Cloud works. **Fan control entities are not yet wired up** — that lands in the next milestones.

Custom Home Assistant integration for the **Dreame Bladeless Fan MF10** (`dreame.fan.u2519`).
Cloud-first via the Dreamehome API. No local API is assumed.

## Supported devices

| Model ID            | Name                       |
|---------------------|----------------------------|
| `dreame.fan.u2519`  | Dreame Bladeless Fan MF10  |

Other Dreame fan models are out of scope for now, though the architecture
is designed to support more via a model-capability map later.

## What works today (M0)

- Config flow from the UI: sign in with Dreamehome credentials + region.
- Real authentication against the Dreame Cloud (no placeholder).
- Discovery: only accounts containing `dreame.fan.u2519` succeed.
- Config entry is created; the integration loads without errors.

## What does NOT work yet

- No `fan` entity — you can't turn the device on/off from HA yet.
- No polling, no sensors, no switches.
- The MiOT property map for MF10 is **unknown** — needs to be discovered.

See [specs/prompt_coding_agent_dreame_mf_10_home_assistant.md](specs/prompt_coding_agent_dreame_mf_10_home_assistant.md) for the full roadmap.

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

```
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

```
custom_components/dreame_mf10/   # the integration itself
specs/                           # authoritative project spec
plans/                           # per-milestone implementation plans
sessions/                        # development session logs
docs/                            # verified technical docs
research/                        # property scan snapshots & diffs (gitignored)
```

## Credits

The Dreame Cloud auth and command flow is adapted from
[CodyJon/dreame-ap10-integration](https://github.com/CodyJon/dreame-ap10-integration)
(originally a sync `requests` implementation; here ported to async
`aiohttp` for native HA compatibility). MiOT property mapping for the
MF10 is **not** reused from AP10 — it is being independently discovered.

## License

TBD. The project is currently a personal work in progress.
