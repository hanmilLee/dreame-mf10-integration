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

## Prossimi passi
1. **Test interattivo MQTT**: `python3 tools/mqtt_listen.py --wildcard`, poi toggle power
   dall'app → osservare se arriva `properties_changed` su (2,1) e se QUALCHE comando passa da MQTT.
2. **Cattura REST corretta**: killare l'app, abilitare SSL proxying su `eu.iot.dreame.tech`
   PRIMA di aprire l'app (così la connessione è decifrata dall'inizio), poi toggle power →
   il `sendCommand` dovrebbe comparire (sconfigge l'ipotesi connessione persistente).
3. Esplorare la pista REST `cn-airp.dreame.tech` / `/airpdev/` (mai indagata).

## Advisor
Consultato prima di scrivere il client MQTT. Issue sollevata: stavo per costruire un PUBLISHER
MQTT mentre la mia stessa evidenza diceva MQTT=ricezione. Corretto: costruito un SUBSCRIBER,
preso l'auth da ioBroker (sorgente leggibile) invece che dall'asm strippato, mantenuta aperta
la pista REST cn-airp. Tutte le raccomandazioni accolte.
