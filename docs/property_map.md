# MiOT Property Map — dreame.fan.u2519 (MF10)

Validated empirically via a before/after diff workflow
(`dev/tools/scan_properties.py` + `dev/tools/diff_properties.py`).

Device: `dreame.fan.u2519` · DID: `<DID>` · Region: `eu`
Firmware: 1035 / Plugin 104

## Validated properties

| Property | siid | piid | Type | Values |
|----------|------|------|------|--------|
| power | 2 | 1 | int | 1 = ON, 2 = OFF — indicatore **read-only** (set_properties → 80001). On/off via action 2/1 (vedi sotto) |
| mode | 2 | 3 | int | see mode table below |
| fan_speed | 2 | 4 | int | 1–10 (min–max) |
| child_lock | 2 | 5 | int | 0 = OFF, 1 = ON |
| blade_oscillation | 2 | 6 | int | 0 = nessuna, 1 = sinistra, 2 = destra, 3 = entrambe |
| device_rotation | 2 | 7 | int | 0 = off, 1 = on (rotazione del dispositivo su se stesso) |
| sync_oscillation | 2 | 11 | int | 0 = off, 1 = on (pale si muovono in sincrono) |
| staggered_oscillation | 2 | 12 | int | 0 = off, 1 = on (pale sfasate) — si esclude con sync |
| continuous_monitoring | 2 | 10 | int | 0 = off, 1 = on (TempSync / monitoraggio continuo) |
| key_tone | 6 | 7 | int | 0 = off, 1 = on (tono tasti / beep) |
| display | 6 | 11 | int | 0 = off, 1 = on (display LED) |
| off_timer | 2 | 8 | int | 0 = disattivato, N = ore (timer spegnimento automatico) |
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

### Power on/off

`piid=1` is a **read-only** state indicator (1 = ON, 2 = standby); writing it via
`set_properties` returns code 80001 in any state. On/off is controlled by the
**action** `siid=2, aiid=1` instead — see the Action map below.

While in standby the device stays on WiFi and accepts `mode`, `fan_speed` and
`oscillation` commands normally.

## Action map — siid=2

**POWER** — on/off via action con argomento di input:

| aiid | params (`in`) | Effetto |
|------|---------------|---------|
| 1 | `[{piid:1, value:1}]` | **POWER ON** — validato sul device reale e in HA |
| 1 | `[{piid:1, value:0}]` | **POWER OFF** — validato |
| 1 | `[]` (vuoti) | ⚠️ **Reset WiFi** |
| 2 | `[]` (vuoti) | ⚠️ Reset WiFi |
| 3 | `[]` (vuoti) | ⚠️ Reset WiFi (80001¹ ma esegue) |

¹ Il codice 80001 su aiid=3 con params vuoti non indica "device irraggiungibile": la relay
restituisce 80001 perché il device si disconnette durante l'esecuzione del reset.

**Chiave**: l'action `aiid=1` con l'argomento `in=[{piid:1,value}]` è il power on/off legittimo
(quello che usa l'app). Con `in` VUOTO la stessa action resetta il WiFi. L'app usa REST `sendCommand` su endpoint IP-based. `coordinator.async_set_power`
hardcoda l'argomento → il payload-reset è irraggiungibile dall'integrazione.
Nota: AP10 usa `siid=2, aiid=3` come power toggle; su MF10 il power è invece aiid=1 con input.

## Invalid candidates (envelope 80001)

The following `(siid, piid)` pairs from `MF10_PROPERTY_CANDIDATES` were
probed and rejected by the backend (device doesn't expose them):

| siid | piid | original label |
|------|------|----------------|
| 3 | 1 | temperature alt |
| 3 | 3 | temperature alt |
| 6 | 5 | display_light |
| 6 | 8 | display_light alt |

## Unidentified (non ancora mappate)

| siid | piid | valore osservato | ipotesi |
|------|------|-----------------|---------|
| 2 | 2 | sempre 0 | sconosciuta — invariante in tutti i test |
| 4 | 1 | sempre 100 | configurazione hardware read-only — scopo sconosciuto |
| 4 | 2 | sempre 180 | **PERICOLOSA** — write con value=90 bypasssa (2,4) e imposta motore in scala raw (ha mostrato "speed 13"). Non usare nell'integrazione. |
| 6 | 4 | sempre 0 | sconosciuta |

## Non rilevabile via get_properties

| Feature | Nota |
|---------|------|
| Velocità oscillazione pale (standard/rapido) | Non muta alcuna property leggibile — probabilmente parametro contestuale nel comando oscillazione |
