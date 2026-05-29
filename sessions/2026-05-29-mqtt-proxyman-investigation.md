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

## Prossimi passi (2 strade)

1. **Cattura REST pulita** (raccomandata dall'advisor, mai fatta bene): killare COMPLETAMENTE
   l'app → abilitare SSL proxying per `eu.iot.dreame.tech` **E** `cn-airp.dreame.tech` PRIMA di
   riaprire → toggle power. Il "nessun sendCommand visto" finora non è affidabile perché la
   connessione all'host comando poteva essere già aperta (non decifrata dal primo byte).
   Focus su `cn-airp.dreame.tech`/`/airpdev/` (pagina di controllo, mai esplorata).

2. **Cattura trasparente mitmproxy** (conclusiva ma più setup): Mac come hotspot + mitmproxy
   `--mode transparent --tcp-hosts 'mt\.eu\.iot\.dreame\.tech'` → cattura TUTTO incluso MQTT
   porta 19973. Risolve definitivamente REST-vs-MQTT e rivela il comando esatto.
2. **Cattura REST corretta**: killare l'app, abilitare SSL proxying su `eu.iot.dreame.tech`
   PRIMA di aprire l'app (così la connessione è decifrata dall'inizio), poi toggle power →
   il `sendCommand` dovrebbe comparire (sconfigge l'ipotesi connessione persistente).
3. Esplorare la pista REST `cn-airp.dreame.tech` / `/airpdev/` (mai indagata).

## Advisor
Consultato prima di scrivere il client MQTT. Issue sollevata: stavo per costruire un PUBLISHER
MQTT mentre la mia stessa evidenza diceva MQTT=ricezione. Corretto: costruito un SUBSCRIBER,
preso l'auth da ioBroker (sorgente leggibile) invece che dall'asm strippato, mantenuta aperta
la pista REST cn-airp. Tutte le raccomandazioni accolte.
