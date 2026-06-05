# MiOT Property Map — dreame.fan.u2519 (MF10)

Validated empirically via a before/after diff workflow
(`dev/tools/scan_properties.py` + `dev/tools/diff_properties.py`).

Device: `dreame.fan.u2519` · DID: `<DID>` · Region: `eu`
Firmware: **1043 / Plugin 116** (aggiornato 2026-06-05; in precedenza 1035 / Plugin 104)

> ⚠️ **L'aggiornamento firmware 1035→1043 ha spostato alcune property MiOT.**
> Vedi la sezione [Firmware migration history](#firmware-migration-history) in fondo.
> Le posizioni nella tabella sotto sono quelle **fw1043 validate empiricamente**.

## Validated properties (fw1043)

| Property | siid | piid | Type | Values |
|----------|------|------|------|--------|
| power | 2 | 1 | int | 1 = ON, 2 = OFF — indicatore **read-only** (set_properties → 80001). On/off via action 2/1 (vedi sotto) |
| mode | 2 | 3 | int | see mode table below |
| fan_speed | 2 | 4 | int | 1–10 (min–max) |
| child_lock | 6 | 10 | int | 0 = OFF, 1 = ON — **spostata da (2,5) in fw1043** |
| blade_oscillation | 2 | 8 | int | 0 = nessuna, 1 = sinistra, 2 = destra, 3 = entrambe — **spostata da (2,6) in fw1043** |
| device_rotation | 2 | 7 | int | 0 = off, 1 = on (rotazione del dispositivo su se stesso) |
| sync_oscillation | 2 | 9 | int | 0 = off, 1 = on (pale in sincrono) — **spostata da (2,11) in fw1043** |
| staggered_oscillation | 2 | 12 | int | 0 = off, 1 = on (pale sfasate) — si esclude con sync |
| temperature | 3 | 2 | int | °C, read-only ambient sensor |

### Rimosse dall'integrazione in fw1043

Queste property non sono più esposte come entità HA. Vedi la storia di migrazione per il dettaglio.

| Property | fw1035 | Motivo |
|----------|--------|--------|
| key_tone | (6,7) | Property dinamica: ritorna 80001 quando OFF, 1 quando ON → rompe il batch polling |
| display LED | (6,11) | (6,11) in fw1043 ritorna la stringa timezone (`Europe/Rome`), non è più il LED |
| off_timer | (2,8) | (2,8) è ora `blade_oscillation`; nuova posizione del timer non identificata |
| continuous_monitoring | (2,10) | Semantica cambiata (legge 1 o 2, mai 0); comportamento non confermato |

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

## Firmware migration history

### 1035 / Plugin 104 → 1043 / Plugin 116 (2026-06-05)

L'aggiornamento firmware ha **spostato la posizione (siid,piid) di alcune property**
nello schema MiOT. L'app ufficiale non se ne accorge perché scarica lo schema
versionato dal cloud ad ogni avvio; la nostra integrazione ha la mappa hardcoded,
quindi un singolo `get_properties` batch con una property non più esistente veniva
respinto con `code=80001` sull'intero envelope → `Failed setup` del coordinator.

Property **spostate** (nuova posizione identificata via diff before/after dall'app):

| Property | fw1035 | fw1043 |
|----------|--------|--------|
| child_lock | (2,5) | **(6,10)** |
| blade_oscillation | (2,6) | **(2,8)** |
| sync_oscillation | (2,11) | **(2,9)** |

Property **rimosse** dall'integrazione (non rimappate):

| Property | fw1035 | Motivo |
|----------|--------|--------|
| key_tone | (6,7) | Dinamica: 80001 quando OFF, 1 quando ON — incompatibile col batch polling |
| display LED | (6,11) | (6,11) ora restituisce la stringa timezone, non più il LED |
| off_timer | (2,8) | (2,8) è ora blade_oscillation; nuova posizione del timer sconosciuta |
| continuous_monitoring | (2,10) | Semantica cambiata (legge 1 o 2, mai 0); non confermata |

**Comportamento diagnostico del cloud in fw1043**: sondando una property che non esiste
più alla vecchia posizione, il relay non restituisce un errore pulito ma o **omette**
l'item dal response batch, o **sostituisce** con un'altra property (es. sondando (2,11)
si riceve un item etichettato (2,1)). Per questo il coordinator fa match per
`(siid,piid)` dell'item ritornato, non per posizione nella richiesta.

Sessione di dettaglio: [dev/sessions/2026-06-05-firmware-1043-property-migration.md](../dev/sessions/2026-06-05-firmware-1043-property-migration.md).
