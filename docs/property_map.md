# MiOT Property Map — dreame.fan.u2519 (MF10)

Validated empirically on 2026-05-22 via before/after diff workflow
(`tools/scan_properties.py` + `tools/diff_properties.py`).

Device: `dreame.fan.u2519` · DID: `-115387050` · Region: `eu`
Firmware: 1035 / Plugin 104

## Validated properties

| Property | siid | piid | Type | Values |
|----------|------|------|------|--------|
| power | 2 | 1 | int | 1 = ON, 2 = OFF — **read-only via cloud relay** (set_properties → code=80001) |
| mode | 2 | 3 | int | see mode table below |
| fan_speed | 2 | 4 | int | 1–10 (min–max) |
| child_lock | 2 | 5 | int | 0 = OFF, 1 = ON |
| oscillation | 2 | 7 | int | 0 = OFF, 1 = ON |
| temperature | 3 | 2 | int | °C, read-only ambient sensor |

### Mode values (siid=2, piid=3)

| Value | Label (app IT) | Label (code) | Display |
|-------|----------------|--------------|---------|
| 0 | Automatica (AI) | `ai` | `F1` |
| 1 | Potente | `powerful` | `F4` |
| 2 | Sonno | `night` | `F2` |
| 3 | Manuale | `manual` | velocità (es. `5`) |
| 7 | Naturale | `natural` | `F3` |

Note: values are non-contiguous (0–3, then 7). No mode at 4, 5, 6 visible
from the Dreamehome app. Other values may exist but are unreachable from UI.

### Display codes (LED sul device)

I codici `F1`–`F4` sul display fisico indicano la modalità attiva — **non sono errori**:

| Display | Modalità | MiOT value |
|---------|----------|------------|
| `F1` | AI (automatica) | 0 |
| `F2` | Sonno (Sleep) | 2 |
| `F3` | Naturale | 7 |
| `F4` | Potente | 1 |
| numero (es. `5`) | Manuale — mostra la velocità corrente | 3 |

In modalità Manuale il display mostra la velocità (1–10), non un codice F.

### Power off behavior

`set_properties(siid=2, piid=1, value=2)` → device stops (hard off).
The "soft off" behavior (OFF_BEHAVIOR_SOFT: set speed to min before off)
is deferred until `async_unload_entry` / options flow in M4 hardening.

## Invalid candidates (envelope 80001)

The following `(siid, piid)` pairs from `MF10_PROPERTY_CANDIDATES` were
probed and rejected by the backend (device doesn't expose them):

| siid | piid | original label |
|------|------|----------------|
| 3 | 1 | temperature alt |
| 3 | 3 | temperature alt |
| 6 | 5 | display_light |
| 6 | 8 | display_light alt |

## Unidentified (always constant, not yet mapped)

| siid | piid | observed value | hypothesis |
|------|------|----------------|-----------|
| 2 | 2 | always 0 | unknown — did not change across any test |
| 6 | 7 | always 1 | NOT child_lock (confirmed) — possibly buzzer or display |

## Discovery methodology

1. `python tools/scan_properties.py --label <before> --did -115387050 --candidates-only`
2. Change one function from Dreamehome app.
3. `python tools/scan_properties.py --label <after> --did -115387050 --candidates-only`
4. `python tools/diff_properties.py research/snapshots/<before>.json research/snapshots/<after>.json`
5. Repeat for each function.

Tests performed this session:

| Test | property changed | finding |
|------|-----------------|---------|
| Power OFF → ON | (2,1): 2→1, (2,4) changed | power=ON=1, power=OFF=2 |
| Power ON → OFF | (2,1): 1→2, (2,4) changed | confirmed |
| Mode Sleep | (2,3): 0→2, (2,4): 8→1 | mode sleep=2 |
| Mode Manuale + speed 5 | (2,3): 2→3, (2,4): 1→5 | mode manual=3, speed confirmed |
| Mode Naturale | (2,3): 3→7, (2,4): 5→2 | mode natural=7 |
| Mode Potente | (2,3): 7→1, (2,4): 2→10 | mode powerful=1 |
| Child lock ON | (2,5): 0→1 | child_lock=1 |
| Child lock OFF | (2,5): 1→0 | child_lock=0, confirmed |

Temperature (3,2) changed naturally across tests (ambient drift) — confirmed read-only sensor.

## Next discovery targets

- `(2,2)`: probe with oscillation toggle (if device has swing feature) or
  natural wind speed variation. Currently always 0.
- `(6,7)`: always 1. Try buzzer/beep toggle or display on/off from app
  settings if available.
- Additional siid/piid outside candidate range: deferred to Phase 2.
