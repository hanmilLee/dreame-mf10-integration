# MiOT Property Map — dreame.fan.u2519 (MF10)

Validated empirically on 2026-05-22 via before/after diff workflow
(`tools/scan_properties.py` + `tools/diff_properties.py`).

Device: `dreame.fan.u2519` · DID: `-115387050` · Region: `eu`
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

### Power off behavior

`set_properties(siid=2, piid=1, value=*)` → **non funziona via cloud relay** (errore 80001
per qualsiasi valore). On/off non è controllabile da HA. Usare il tasto fisico o
l'app Dreamehome.

Importante: questo non significa che il device sia irraggiungibile via cloud
quando è spento. I comandi `mode`, `fan_speed` e `oscillation` inviati da HA
arrivano comunque al device anche con `power=2` (beep fisico confermato).
Il problema è specifico del comando di accensione/spegnimento reale: il device
riceve property operative, ma non le interpreta come transizione `OFF → ON`.

Snapshot già disponibili in `research/snapshots/`:

| Diff | Cambi osservati |
|------|-----------------|
| `initial-candidates` → `after-power-on` | `(2,1): 2→1`, `(2,4): 6→8` |
| `after-power-on` → `after-power-off` | `(2,1): 1→2`, `(2,4): 8→6` |
| `after-power-off` → `after-mode-sleep` | `(2,1): 2→1`, `(2,3): 0→2`, `(2,4): 6→1` |

Il terzo diff era fuorviante: testato via API (`set_properties(mode=2)` da standby)
il device riceve il comando (beep) ma `power` rimane 2. Il cambio `power 2→1` in quel
diff era causato da un'interazione fisica dell'utente, non dal comando API.

**Confermato 2026-05-28**: `piid=1` è read-only sia da standby che da ON.
`set_properties(piid=1, value=2)` con device fisicamente ON → code=80001.

## Action map — siid=2

**POWER (RISOLTO 2026-05-29)** — on/off via action con argomento di input:

| aiid | params (`in`) | Effetto |
|------|---------------|---------|
| 1 | `[{piid:1, value:1}]` | **POWER ON** — validato sul device reale e in HA |
| 1 | `[{piid:1, value:0}]` | **POWER OFF** — validato |
| 1 | `[]` (vuoti) | ⚠️ **Reset WiFi** — confermato 2026-05-23 |
| 2 | `[]` (vuoti) | ⚠️ Reset WiFi — confermato 2026-05-23 |
| 3 | `[]` (vuoti) | ⚠️ Reset WiFi — confermato 2026-05-23/26 (80001¹ ma esegue) |

¹ Il codice 80001 su aiid=3 con params vuoti non indica "device irraggiungibile": la relay
restituisce 80001 perché il device si disconnette durante l'esecuzione del reset.

**Chiave**: l'action `aiid=1` con l'argomento `in=[{piid:1,value}]` è il power on/off legittimo
(quello che usa l'app). Con `in` VUOTO la stessa action resetta il WiFi. Scoperto via cattura
MITM dell'app (l'app usa REST `sendCommand` su endpoint IP-based). `coordinator.async_set_power`
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

## Discovery methodology

1. `python tools/scan_properties.py --label <before> --did -115387050 --candidates-only`
2. Change one function from Dreamehome app.
3. `python tools/scan_properties.py --label <after> --did -115387050 --candidates-only`
4. `python tools/diff_properties.py research/snapshots/<before>.json research/snapshots/<after>.json`
5. Repeat for each function.

Tests performed this session (2026-05-22):

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

Tests performed this session (2026-05-28):

| Test | property changed | finding |
|------|-----------------|---------|
| Oscillazione pala sinistra ON | (2,6): 0→1 | blade_oscillation sinistra=1 |
| Oscillazione pala sinistra OFF | (2,6): 1→0 | confermato |
| Oscillazione pala destra ON | (2,6): 0→2 | blade_oscillation destra=2 |
| Oscillazione entrambe le pale ON | (2,6): 2→3 | blade_oscillation entrambe=3 |
| Oscillazione sfalsata ON | (2,12): 0→1 | staggered_oscillation=1 |
| Oscillazione sfalsata OFF | (2,12): 1→0 | confermato |
| Oscillazione sincronizzata ON | (2,11): 0→1 | sync_oscillation=1 |
| Oscillazione sincronizzata OFF | (2,11): 1→0 | confermato |
| Entrambe pale indipendenti | (2,11)=0, (2,12)=0, (2,6)=3 | default quando nessun pattern attivo |
| `piid=1=2` con device ON | — | 80001 — read-only anche da ON (definitivo) |
| siid=11–20 piid=1–5 (50 probes, device standby) | — | tutto 80001 — siid non esistono |

## Next discovery targets

- `(2,2)`, `(2,8)`: sempre 0 — da testare con funzioni non ancora mappate.
- `(2,7)`: sempre 0 in tutti i test oscillazione — da testare con altre feature.
- `(2,10)`: sempre 1 — da testare.
- `(6,7)`: sempre 1 — provare buzzer/beep toggle o display on/off dall'app.
