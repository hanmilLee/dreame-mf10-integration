# Sessione 2026-05-29 — Cattura Proxyman + canale MQTT vs REST per power

## Obiettivo
Identificare il canale e il comando esatto con cui l'app Dreamehome accende/spegne
il MF10, dopo aver confermato che `set_properties`/`action` REST non funzionano sul power.

## Punto di partenza
Da `plans/power-on-off-investigation.md`: esauriti i probe MiOT non distruttivi.
Strade aperte: F1 (metodi legacy), G1 (endpoint alternativi), H1 (Proxyman), I1 (Mi Home).

## Prove raccolte oggi

### F1 — Metodi MIIO legacy (REST sendCommand con method arbitrario)
Aggiunto `--raw-method` a `tools/call_action.py`. Testati con device in standby:

| method | params | esito |
|--------|--------|-------|
| `set_power` | `["on"]`, `[1]`, `{"power":"on"}` | code=80001 |
| `power_on` | `["on"]` | code=0 MA risposta = get_properties cached (NON accende) |
| `power_on` | `[]` | code=80001 |
| `power_off` | `["off"]` | code=80001 |
| `app_start`, `device_on` | `["on"]` | code=80001 |

`power_on` con `["on"]` ha dato code=0 ma la risposta era lo stato cached di tutte le
property note (comportamento anomalo del relay su method sconosciuti) — il device è
rimasto in standby. Nessun metodo legacy accende.

### G1 — Endpoint REST alternativi (analisi CodyJon/dreame-ap10-integration)
`api.py` di CodyJon usa lo STESSO e unico endpoint `/dreame-iot-com{host}/device/sendCommand`.
Nessun path alternativo. Conferma anche che sull'AP10 `set_properties(2,1)` va in timeout —
stessa situazione del MF10. Il power AP10 è `action(2,3)` — ma sul MF10 quell'action è WiFi reset.

### H1 — Cattura Proxyman (4 sessioni)
File estratti in `tmp/ps*/`. Risultato chiave:

- Il proxy HTTP di iOS intercetta SOLO HTTP/HTTPS. Il broker MQTT (porta 19973) è TCP
  grezzo → **bypassa Proxyman, non compare mai in nessuna cattura**.
- Sessione 14:09 (decryption perfetta su tutti gli host Dreame): durante un ciclo
  completo ON/OFF **+ cambio mode** dall'app, l'UNICO traffico Dreame mutante è stato:
  - `POST eu.iot.dreame.tech/smart-app/meari-cloud/redirect` → cloud telecamere Meari, irrilevante
  - `GET cn-airp.dreame.tech/airpdev/system/snmac/<MAC>` ×3 → heartbeat, risponde `{code:200}`
  - **Zero `sendCommand`, zero POST comando, zero WebSocket, zero broker MQTT**
- La pagina di dettaglio del device (da cui si accende) chiama `cn-airp.dreame.tech`,
  non `eu.iot.dreame.tech`.

Spiegazioni possibili del comando mancante: (a) MQTT porta 19973 invisibile al proxy,
(b) connessione HTTP/2 persistente aperta PRIMA di abilitare la decryption → invisibile.

### Analisi decompilato app (tmp/blutter-output, tmp/dreamehome-apk)
- `HomeRepository::sendCommand` → `ApiClient::sendCommand` → `/device/sendCommand` = i comandi
  vanno via REST.
- `DMMqttManager` è **solo ricezione** (handleDeviceMessage, subscribe a `/status/ /msg/ /w/`).
- Broker MQTT usa **mutual TLS**: `assets/cert/{cacert.pem,client.pem,client.key}` — estratti
  in `tmp/dreamehome-apk/certs/` (cert condiviso `CN=client`, valido fino al 2969).
- Metodi MiOT presenti: `set_properties`, `get_properties`, `action`.
- Broker stringa: `10000.mt.cn.iot.dreame.tech:19973` (CN; il nostro è `.eu.`).

### Riferimento decisivo — TA2k/ioBroker.dreame (codice in chiaro)
Salvato in `/tmp/iobroker_dreame_main.js`. Conferma:

- **MQTT = solo ricezione**. Connect con `clientId='p_'+8bytehex`, `username=uid`,
  `password=access_token`, `rejectUnauthorized:false`, **nessun cert client**.
  Subscribe: `/status/{did}/{uid}/{model}/eu/`. Messaggi in arrivo: `method:"properties_changed"`.
- **Comandi = REST `sendCommand`** (`set_properties`/`action`), STESSO endpoint nostro.
- Il payload `sendCommand` di ioBroker include un campo **`from`** dentro `data` che NOI non
  mandiamo: `data:{did,id,method,params,from:<uid?>}`.

### Test campo `from` (tools/test_from_field.py)
Testato `set_properties(2,1,value=1)` con `from` = uid / did / "" su device in standby:
- **Tutti code=80001**. Il campo `from` NON sblocca il power. `(2,1)` è read-only confermato.

## Conclusioni consolidate (2026-05-29)
1. MQTT è solo ricezione (confermato da ioBroker + decompilato). Costruire un publisher MQTT
   è la strada sbagliata.
2. I comandi vanno via REST `sendCommand`.
3. `set_properties(2,1)` = read-only (fallisce anche con `from`). `action(2,1/2/3)` = WiFi reset.
4. Il power-on dell'app NON è un set_properties su (2,1) né un metodo legacy noto.
5. Il comando power dell'app non è stato catturato: o è su un canale invisibile al proxy HTTP,
   o su connessione persistente non decifrata.

## Strumenti creati/aggiornati
- `tools/call_action.py`: aggiunto `--raw-method`/`--raw-params` (method REST arbitrario)
- `tools/test_from_field.py`: test campo `from` nel payload sendCommand
- `tools/mqtt_listen.py`: subscriber MQTT al broker Dreame — **connessione VERIFICATA OK**
  (clientId/uid/token, no cert, rejectUnauthorized off). Iscrizione a `/status/...` o `#`.

## Test MQTT interattivo — ESEGUITO (14:32)

`mqtt_listen.py --wildcard` con toggle ON/OFF dall'app:

- `#` → **NEGATO (ACL)**: il broker concede solo i topic del proprio account.
- `/status/{did}/{uid}/{model}/eu/` → **OK qos=0**.
- Toggle ON dall'app → ricevuto `properties_changed` con `(2,1)=1` + dump completo.
- Toggle OFF dall'app → ricevuto `properties_changed` con `(2,1)=2` + dump completo.

Conclusioni:
- **Il device notifica on/off via MQTT `/status/` in tempo reale** → utilizzabile per push
  state nell'integrazione (al posto del polling 30s).
- Questo è il device che NOTIFICA (device→cloud→noi), NON il comando dell'app (app→device).
  Il topic su cui l'app pubblica i comandi non è sottoscrivibile (ACL nega `#`).
- **Nuova property: `(6,30)=1`** — non era nelle 19 note. Da identificare.
- Dump completo on power-change include anche `(6,4)=0` (già nota read-only).

## Test sottoscrizione topic comando — ESEGUITO (14:38)

`mqtt_listen.py --cmd-topics`: sottoscrizione a `/status/` + candidati `/w/ /msg/ /p/ /r/ /c/
/iot/ /down/ /set/` (suffisso `{did}/{uid}/{model}/eu/`).

- `/status/` → **OK**. Tutti gli altri → **NEGATO (ACL)**.
- Toggle ON/OFF da app → di nuovo solo `properties_changed` su `/status/` (2,1: 1→2).

Conclusione: i topic comando sono **publish-only** per le nostre credenziali (ACL nega la
sottoscrizione ma probabilmente consente la pubblicazione). L'app ci scrive i comandi; noi
possiamo solo leggere `/status/`. → Esperimento publish ora giustificato (advisor esito 3).

## Esperimento publish MQTT — ESEGUITO (14:41)

`mqtt_publish.py --safe-test`: pubblicato `set_properties(6,11)` (toggle display, innocuo) su
8 topic candidati `/w/ /msg/ /p/ /r/ /c/ /iot/ /down/ /set/` (suffisso `{did}/{uid}/{model}/eu/`),
con `/status/` sottoscritto per verifica.

- Tutti i publish "confermati" localmente (QoS0), ma **nessuna eco** su `/status/` → device non reagisce.
- Verifica QoS1 su `/w/`: **PUBACK ricevuto** → il broker ACCETTA il nostro publish su `/w/`
  (nessuna disconnessione ACL). Ma il device non agisce.

Interpretazione: `/w/{did}/{uid}/{model}/eu/` è accettato dal broker ma **non è il topic di
comando del device**. Il device non è user-scoped: ascolta probabilmente un topic basato su
`did`/`model` senza `uid`, che non possiamo indovinare con certezza né leggere (ACL) né
sniffare (proxy HTTP non vede MQTT). Combinato con decompilato + ioBroker (comandi = REST),
l'ipotesi più probabile resta: **i comandi vanno via REST**, non MQTT.

## Cattura REST PULITA — ESEGUITA (15:03) — DECISIVA

Due tentativi:
- ps5 (14:57): `eu.iot.dreame.tech` rimasto `CONNECT`. Causa: wildcard `*.dreame.tech` matcha
  un solo livello → prende `cn-airp` ma NON `eu.iot` (due etichette). Pattern corretti: host esatti.
- ps6 (15:03): pattern `eu.iot.dreame.tech` + `cn-airp.dreame.tech` (esatti). **Entrambi decifrati
  dal primo byte** (app killata e riaperta), toggle power durante cattura.

Risultato: l'UNICO traffico REST durante il toggle è `meari-cloud/redirect` (telecamere) +
`snmac` heartbeat (`code:200`). **Nessun `sendCommand`, nessun comando, su nessun host REST.**

### CONCLUSIONE DEFINITIVA

Il comando power **NON viaggia via REST**. Va via **MQTT** (porta 19973), invisibile al proxy
HTTP di iOS. Il device riceve il comando sul proprio topic di comando (ACL ci nega la lettura)
e poi notifica lo stato su `/status/`. Per i comandi realtime (power/mode), l'app MF10 usa MQTT
publish — diversamente da ioBroker (vacuums via REST). Il `sendCommand` REST resta valido per
get/set delle property operative, ma il power non è esposto come property scrivibile via REST.

## MITM trasparente mitmproxy WireGuard — ESEGUITO (15:24-15:27) — BLOCCATO da pinning

Setup: `mitmdump --mode wireguard --tcp-hosts 'mt\.eu\.iot\.dreame\.tech' --set
client_certs=client-combined.pem -s tools/mitm_mqtt_addon.py`. iPhone via tunnel WireGuard
(QR), CA mitmproxy installata e trustata.

Risultato:
- **Porta 19973** (`mt.eu.iot.dreame.tech`, broker device): solo "TCP flow aperto" in reconnect
  loop, MAI un CONNECT decodificato → **l'app rifiuta il cert di mitmproxy = PINNING**. L'app usa
  SecurityContext custom con `cacert.pem` (GlobalSign) bundleato. Mentre il MITM intercetta, il
  comando non parte (device non reagisce fisicamente). **MITM bloccato sul canale del ventilatore.**
- **Porta 1883** (Alibaba 8.209.x, IN CHIARO): decodificato CONNECT + SUBSCRIBE, ma è un servizio
  DIVERSO — topic `$bsssvr/iot/{thing}/{clientId}/event/update/accepted`,
  `$bsssvr/iot/presence/disconnected/{thing}`. Presence/eventi, NON comando ventilatore.
  clientId numerico, username base64, thing-id 32-hex (non il nostro did/mac).

Conclusione: il comando ventilatore è sul 19973 TLS-pinnato. **Transparent MITM non può decifrarlo.**

Verifica aggiuntiva (15:32): aggiunto al addon il log HTTP (eventuale comando REST di fallback).
Toggle con device che reagisce fisicamente → di nuovo NESSUN PUBLISH, NESSUN HTTP comando, solo
reconnect loop 19973 + `$bsssvr` di avvio sul 1883. Il comando non transita su nessun canale
leggibile (1883 chiaro né HTTP). **MA**: la conclusione "MQTT" era ERRATA → vedi sotto.

## ⭐ COMANDO POWER TROVATO (15:36) — è REST action siid=2 aiid=1

Il filtro HTTP dell'addon escludeva gli host IP (l'app usa l'endpoint per IP, non hostname:
`47.254.176.95:13267`, ecco perché Proxyman per-hostname lo mancava). Corretto il filtro per
PATH → catturati i `sendCommand` con body. Toggle ON/OFF dall'app:

- **POWER ON**: `method=action params={siid:2, aiid:1, in:[{piid:1,value:1}]}` → resp code:0,
  poi `get(2,1)=1`.
- **POWER OFF**: `method=action params={siid:2, aiid:1, in:[{piid:1,value:0}]}` → resp code:0,
  poi `get(2,1)=2`.

**Perché ci resettava il WiFi**: avevamo chiamato `action 2 aiid=1` con params VUOTI. Senza
l'argomento `in=[{piid:1,value:X}]` l'azione fa reset; CON l'argomento è il power toggle.
Dettagli payload app: `from` dentro data (`"ios"`/instance-id), `sign`+`timestamp` esterni (HMAC,
probabilmente opzionali — i nostri get/set funzionano senza). Vedi memoria [[project_power_command_found]].

**La conclusione "comando = MQTT" precedente è SMENTITA**: è REST, lo mancavamo per il filtro
host. Il 19973 pinnato è solo il canale di stato/notifica, non il comando.

## Stato finale investigazione on/off

Tutte le vie non-invasive esaurite. Il comando power è MQTT publish su broker pinnato.

Vie residue per il comando esatto (invasive):
- **Frida** (pinning-proof): hooka il publish prima del TLS. Serve iPhone jailbroken o IPA repackaged.
- **Repackage APK Android**: sostituire `cacert.pem` nell'APK con la CA di mitmproxy, resign,
  girare su Android → l'app si fida del MITM. Serve device/emulatore Android.

## Prossimi passi (raccomandati)

1. **Win shippabile**: integrare subscribe MQTT `/status/` nell'integrazione HA per state push
   realtime (power + property) al posto del polling 30s. Indipendente dal comando on/off.
   Vedi memoria [[project_mqtt_push_state]]. Riusare `tools/mqtt_listen.py`.
2. Mappare la nuova property `(6,30)`.
3. (Opzionale, invasivo) Frida o repackage APK per il comando power.
2. **Cattura REST corretta**: killare l'app, abilitare SSL proxying su `eu.iot.dreame.tech`
   PRIMA di aprire l'app (così la connessione è decifrata dall'inizio), poi toggle power →
   il `sendCommand` dovrebbe comparire (sconfigge l'ipotesi connessione persistente).
3. Esplorare la pista REST `cn-airp.dreame.tech` / `/airpdev/` (mai indagata).

## Advisor
Consultato prima di scrivere il client MQTT. Issue sollevata: stavo per costruire un PUBLISHER
MQTT mentre la mia stessa evidenza diceva MQTT=ricezione. Corretto: costruito un SUBSCRIBER,
preso l'auth da ioBroker (sorgente leggibile) invece che dall'asm strippato, mantenuta aperta
la pista REST cn-airp. Tutte le raccomandazioni accolte.
