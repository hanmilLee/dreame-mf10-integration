# Piano di investigazione — Power ON/OFF MF10

## Contesto

`set_properties(siid=2, piid=1, value=1|2)` ritorna sempre `code=80001`,
indipendentemente dallo stato del device (ON o standby). La property è
**dichiarata read-only nel firmware MiOT**: è un indicatore di stato, non
un comando.

L'app Dreamehome **riesce** ad accendere e spegnere il device — quindi
esiste un comando che il nostro client non sta usando. Le strade da
investigare sono elencate qui sotto, in ordine di rischio crescente.

## Stato attuale (cosa è stato già provato)

| Test | Esito |
|------|-------|
| `set_properties(2,1,value=1)` da standby | 80001 |
| `set_properties(2,1,value=2)` da ON | 80001 |
| `set_properties(2,1,value=1)` da standby (riprovato) | 80001 |
| `call_action(siid=2, aiid=1)` | code=0 ma WiFi reset del device |
| `call_action(siid=2, aiid=2)` | code=0 ma WiFi reset del device |
| `call_action(siid=2, aiid=3)` | code=80001 ma WiFi reset del device |
| Scan siid 11–20 piid 1–5 (50 probes) | tutto 80001 — siid non esistono |
| Scan siid 7–10 piid 1–5 | tutto 80001 |
| Scan siid 1 piid 1–5 | tutto 80001 |
| Scan siid 5 piid 1–5 | tutto 80001 |
| Diff completo property note ON vs OFF | solo `(2,1)`, `(2,8)`, `(3,2)` cambiano |
| Scan esteso siid 2 piid 21–40 / siid 3 piid 4–15 / siid 4 piid 9–20 / siid 6 piid 13–25 / siid 21–30 | TODO (in corso) |

## Test elencati per categoria

Ogni test ha: scopo, comando, rischio, criterio di successo, rollback.

---

### Categoria A — Esplorazione esaustiva via letture (rischio: ZERO)

Solo `get_properties` — nessun effetto collaterale possibile.

#### A1 — Scan esteso siid 2 piid 21–100 in stato ON

```bash
# Da implementare: estensione dello script full-scan con range più ampio
python tools/scan_properties.py --did -115387050 --siid-min 2 --siid-max 2 \
  --piid-min 21 --piid-max 100 --label deep-siid2-on
```

**Rischio**: nessuno (lettura)
**Criterio successo**: trovare property reali (non alias) oltre piid=12
**Note**: filtrare risposte dove `siid` o `piid` ricevuto ≠ richiesto (alias del relay)

#### A2 — Scan completo siid 1–50 piid 1–10 (entrambi gli stati)

Trovare l'esistenza completa dei service. Lo scan precedente era limitato.

**Rischio**: nessuno
**Tempo stimato**: ~30 min (500 probes × ~3s medi)

---

### Categoria B — Comandi `set_properties` con payload alternativi (rischio: BASSO)

Probabilmente il firmware risponde con 80001 — nessun effetto persistente noto.

#### B1 — `set_properties` con valore array invece di scalar

```bash
# Vedere se il device accetta value=[1] invece di value=1
python tools/call_action.py --set-prop --siid 2 --piid 1 --value '[1]'
```

#### B2 — `set_properties` con `value` come stringa

```bash
python tools/call_action.py --set-prop --siid 2 --piid 1 --value '"1"'
python tools/call_action.py --set-prop --siid 2 --piid 1 --value '"on"'
```

#### B3 — `set_properties` multi-prop atomico

Forse il firmware accetta `power` solo se accompagnato da altre property.

```bash
# da implementare come script ad-hoc:
# [{siid:2,piid:1,value:1}, {siid:2,piid:3,value:0}, {siid:2,piid:4,value:5}]
```

#### B4 — `set_properties` su `(2,1)` con valori non documentati

`value=0`, `value=3`, `value=99` — magari il firmware ha un trigger su un valore specifico.

```bash
for v in 0 3 4 99 255; do
  python tools/call_action.py --set-prop --siid 2 --piid 1 --value $v
done
```

---

### Categoria C — Property `mode` con valori non documentati (rischio: BASSO/MEDIO)

I valori noti sono 0,1,2,3,7. I gap (4,5,6) e i valori sopra 7 (8+) non sono stati testati.
Potrebbe esistere un `mode=off` che spegne il device.

#### C1 — `mode` da 4 a 15

```bash
for v in 4 5 6 8 9 10 11 12 13 14 15; do
  python tools/call_action.py --set-prop --siid 2 --piid 3 --value $v
  python tools/call_action.py --read-prop --siid 2 --piid 1
done
```

**Rischio**: il device potrebbe passare a una modalità sconosciuta. Recupero via tasto fisico.
**Criterio successo**: trovare un valore di mode che porta `(2,1)` a 1 da standby, o a 2 da ON

#### C2 — `mode=-1` o valori negativi

```bash
python tools/call_action.py --set-prop --siid 2 --piid 3 --value -1
```

---

### Categoria D — Bool con valori non standard (rischio: BASSO)

Sui bool (`device_rotation`, `child_lock`, ecc.) abbiamo testato solo 0/1.
Un valore come 2, 99, -1 potrebbe avere semantica nascosta.

#### D1 — Bool con `value=2`

```bash
for siid_piid in 2,5 2,7 2,10 2,11 2,12 6,7 6,11; do
  s=${siid_piid%,*}; p=${siid_piid#*,}
  python tools/call_action.py --set-prop --siid $s --piid $p --value 2
done
```

**Rollback**: dopo ogni write rileggere e ripristinare a 0/1 se cambia

---

### Categoria E — Action MiOT con aiid > 3 (rischio: ALTO — possibile WiFi reset)

aiid 1, 2, 3 su siid=2 causano reset. Non sappiamo aiid=4+ cosa fa.
**Da fare solo con accordo esplicito**: ogni test potenzialmente richiede re-pairing fisico.

#### E1 — `call_action(siid=2, aiid=4)` con `params=[]`

```bash
python tools/call_action.py --siid 2 --aiid 4 --params '[]'
```

**Rischio**: WiFi reset → re-pairing fisico necessario
**Mitigazione**: lasciare device acceso vicino, app pronta per re-add

#### E2 — `call_action(siid=2, aiid=4)` con `params=[1]` o `params=[2]`

```bash
python tools/call_action.py --siid 2 --aiid 4 --params '[1]'
```

#### E3 — Iterare aiid 5..10 su siid=2

Solo se E1/E2 non causano reset (= aiid=4 esiste e non è distruttiva).
Tutti gli aiid hanno comunque potenziale di reset.

#### E4 — `call_action` su altri siid

```bash
# siid=3 (sensor temp) — improbabile abbia action ma escluderlo
python tools/call_action.py --siid 3 --aiid 1 --params '[]'
# siid=4 (config motore?) — alto rischio
python tools/call_action.py --siid 4 --aiid 1 --params '[]'
# siid=6 (display/sistema)
python tools/call_action.py --siid 6 --aiid 1 --params '[]'
```

---

### Categoria F — Comandi MIIO legacy / Xiaomi pre-MiOT (rischio: BASSO)

Prima di MiOT, Xiaomi usava un protocollo "MIIO" con `method` arbitrari come stringhe.
Il device potrebbe ancora rispondere a questi in fallback.

#### F1 — `method=set_power` con stringa

Modificare `dreame_cloud.py` o uno script ad-hoc per inviare:

```json
{
  "method": "set_power",
  "params": ["on"]
}
```

Invece di `set_properties`.

**Rischio**: il device probabilmente ignora o ritorna errore
**Criterio successo**: device si accende → tracciare l'endpoint usato

#### F2 — Altri method legacy

```text
set_on_off / power_on / power_off / app_set_power / device_on
```

#### F3 — Wrap `set_properties` con un `method` diverso

Il relay usa internamente un `sendCommand` HTTP. Forse esistono altri tipi:

- `device.execute`
- `device.method`
- `controller.execute`

Da identificare leggendo eventuali tracce in `dreame_cloud.py` o nel codice ispirazione `CodyJon/dreame-ap10-integration`.

---

### Categoria G — Endpoint REST alternativi (rischio: BASSO)

Il client attuale usa `https://{region}.iot.dreame.tech:13267` + path `sendCommand`.
Potrebbero esistere altri endpoint con semantica diversa.

#### G1 — Enumerare endpoint noti dal codice di riferimento

Cercare in `dreame_cloud.py` e nel repo `CodyJon/dreame-ap10-integration` tutti i path REST.
Verificare se ce ne sono di non implementati nel nostro client.

#### G2 — Endpoint `device/properties` standalone

Alcuni cloud Xiaomi espongono `POST /device/properties` (non passa per relay).

---

### Categoria H — Cattura traffico app (rischio: BASSO ma laborioso)

Anche se il pinning blocca il payload, l'**host e l'endpoint** sono visibili in chiaro nei
TLS ClientHello.

#### H1 — Proxyman + iPhone, capture passiva (no MITM)

```text
1. iPhone WiFi proxy → Mac IP:9090
2. Non installare certificato → no decrypt, ma vediamo host + path
3. Aprire app Dreamehome → tap on/off → osservare connection list
4. Esportare HAR / pcap
```

**Output atteso**: lista hostname + path che cambia quando si preme on/off
**Criterio successo**: identificare un endpoint diverso da `iot.dreame.tech:13267/sendCommand`

#### H2 — DNS sniffing

Configurare il Mac come DNS server per l'iPhone e loggare le query durante l'accensione.

#### H3 — Tentativo MITM con SSL pinning bypass

- **frida-trace** su un device jailbroken (non disponibile)
- **mitmproxy** con script che modifica TLS handshake — funziona solo se l'app non fa pinning hard
- Provare comunque, fallback se G/H1 non risolvono

#### H4 — Analisi dell'IPA dell'app (rischio: legale incerto)

Decompilare l'app Dreamehome per cercare costanti relative a `power_on`, `set_power`, ecc.
Da fare solo se nient'altro funziona.

---

### Categoria I — Approcci collaterali (rischio: BASSO)

#### I1 — Mi Home app invece di Dreamehome

Il MF10 è un device Xiaomi-ecosystem. Provare ad aggiungerlo alla Mi Home app
e fare la stessa Proxyman capture. Mi Home usa MiOT puro, potrebbe rivelare
il vero comando di power se il device è gestibile da Mi Home.

#### I2 — Contattare supporto Dreame

Richiesta diretta di documentazione MiOT spec del modello (`dreame.fan.u2519`).
Probabile risposta: "non disponibile per consumer".

#### I3 — Cercare su forum cinesi

`dreame.fan.u2519` + `siid piid` + `开关` (interruttore). Già provato senza risultati.

---

## Priorità suggerita

1. **A1/A2** — chiudere definitivamente l'enumerazione property/siid (zero rischio, alto valore)
2. **F1/F3, G1, B3** — provare payload e endpoint alternativi (basso rischio, alto valore)
3. **C1** — testare valori non documentati di mode (basso/medio rischio)
4. **H1** — Proxyman capture passivo per identificare l'endpoint (basso rischio, richiede iPhone)
5. **I1** — Mi Home app (basso rischio, potenzialmente molto rivelatore)
6. **B1/B2/B4, D1** — payload variations (basso rischio)
7. **E1+** — action aiid > 3 (ALTO rischio: ultima carta, solo dopo aver esaurito le altre)
8. **H3/H4** — reverse engineering app (laborioso, ultima carta)

## Rollback / preparazione

Prima di ogni test ad alto rischio (E*, H3):

1. Device acceso fisicamente accessibile
2. App Dreamehome aperta su iPhone per eventuale re-add
3. Credenziali Dreamehome a portata di mano
4. Disponibilità a re-pairing fisico (tasto reset + WiFi setup)

## Log dei test eseguiti

| Data | Test | Esito | Note |
|------|------|-------|------|
| 2026-05-28 | A1 parziale (siid 2 piid 21-40, siid 3 piid 4-15, siid 4 piid 9-20, siid 6 piid 13-25, siid 21-30 piid 1-3) | **nessuna property nuova** (0/87 — 55 alias, 32 80001) | `tmp/full-scan-off.json` |
| 2026-05-28 | Diff property note ON vs OFF (19 prop) | solo `(2,1)` `(2,8)` `(3,2)` cambiano — niente di nuovo | `tmp/full-on.json`, `tmp/full-off.json` |
| 2026-05-28 | A1 dettagliato (stessi 87 probe ON e OFF) — diff completo response per response | **nessuna property reale**. Tutte le differenze ON/OFF sono alias del relay verso `(2,1)`/`(2,4)`/`(4,1)`/`(4,2)` con i loro valori correnti, oppure timeout di rete aleatori | `tmp/full-scan-on-detailed.json`, `tmp/full-scan-off-detailed.json` |

### Conclusione provvisoria (2026-05-28)

Esauriti tutti i probe non distruttivi su siid 1–30 / piid 1–40. La superficie MiOT
esposta dal firmware MF10 è limitata alle 19 property note. Il comando di power
**non è raggiungibile via `get/set_properties` di MiOT standard**.

Strade ancora aperte (in ordine di valore atteso):

1. **F1/F3** — payload alternativi (MIIO legacy `method=set_power`, endpoint relay diversi)
2. **G1** — enumerazione endpoint REST nel codice di riferimento `CodyJon/dreame-ap10-integration`
3. **H1** — Proxyman passivo sull'iPhone per identificare hostname/path usato dall'app
4. **I1** — provare ad aggiungere il device a Mi Home (Xiaomi) invece di Dreamehome
5. **C1** — `mode` con valori non documentati 4/5/6/8+ (basso rischio)
6. **E1+** — action MiOT con aiid > 3 (ALTO rischio: WiFi reset = re-pairing)

(aggiornare riga per riga man mano)
