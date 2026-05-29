"""Publisher MQTT al broker Dreame — trova il topic comando e prova a controllare il device.

Metodologia (advisor-approved, esito ACL publish-only):
  1. Si connette e si iscrive a /status/ (canale di verifica — device→noi).
  2. Pubblica un comando `set_properties` su uno o più topic candidati comando.
  3. Ascolta /status/ per N secondi: se compare un `properties_changed` con la property
     che abbiamo settato → quel topic è il canale comando.

Regole di sicurezza:
  - SOLO `set_properties` di default. Le `action` (rischio WiFi reset su questo device)
    sono bloccate salvo flag esplicito `--allow-action` + conferma interattiva.
  - Test sicuro di default: toggla una property innocua (display 6,11) e verifica l'eco.

Topic candidati (suffisso {did}/{uid}/{model}/{region}/):
    /w/  /msg/  /p/  /r/  /c/  /iot/  /down/  /set/

Uso:
    set -a; source .env; set +a
    # 1. Trova il topic comando con una property sicura (display 6,11 toggle)
    .venv/bin/python tools/mqtt_publish.py --safe-test

    # 2. Una volta trovato il topic, prova il power su quel topic
    .venv/bin/python tools/mqtt_publish.py --topic w --siid 2 --piid 1 --value 1

    # 3. set_properties arbitrario su un topic specifico
    .venv/bin/python tools/mqtt_publish.py --topic w --siid 6 --piid 11 --value 0

Env: DREAME_USERNAME, DREAME_PASSWORD, DREAME_REGION (default eu)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import ssl
import sys
import threading
import time

_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.isfile(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "dreame_mf10"))

import aiohttp
import paho.mqtt.client as mqtt

from dreame_cloud import DreameCloud  # type: ignore[import]

CANDIDATE_PREFIXES = ("w", "msg", "p", "r", "c", "iot", "down", "set")


async def _bootstrap():
    username = os.environ.get("DREAME_USERNAME")
    password = os.environ.get("DREAME_PASSWORD")
    region = os.environ.get("DREAME_REGION", "eu")
    if not username or not password:
        print("ERROR: set DREAME_USERNAME e DREAME_PASSWORD")
        sys.exit(1)
    async with aiohttp.ClientSession() as session:
        cloud = DreameCloud(username, password, region, session)
        await cloud.async_login()
        devices = await cloud.async_get_devices()
        device = next((d for d in devices if "u2519" in d.get("model", "")), devices[0])
        # leggi display (6,11) corrente per il safe-test
        cur = await cloud.async_get_properties(device["did"], [{"siid": 6, "piid": 11}], host=device.get("bindDomain"))
        display_val = None
        for p in cur or []:
            if p.get("siid") == 6 and p.get("piid") == 11 and p.get("code", -1) == 0:
                display_val = p.get("value")
        return (
            cloud._uid, cloud._access_token, str(device["did"]),
            device.get("model", ""), device.get("bindDomain"), region, display_val,
        )


def build_payload(did, siid, piid, value, method="set_properties"):
    """Costruisce il payload MiOT come visto in properties_changed, con method comando."""
    rid = int(time.time()) % 100000
    return json.dumps({
        "id": rid,
        "did": int(did) if str(did).lstrip("-").isdigit() else did,
        "data": {
            "id": rid,
            "method": method,
            "params": [{"did": str(did), "siid": siid, "piid": piid, "value": value}],
        },
    })


def main() -> None:
    parser = argparse.ArgumentParser(description="Publisher MQTT broker Dreame")
    parser.add_argument("--topic", default=None,
                        help=f"Prefisso topic singolo su cui pubblicare ({'/'.join(CANDIDATE_PREFIXES)}). Default: tutti")
    parser.add_argument("--siid", type=int, default=None)
    parser.add_argument("--piid", type=int, default=None)
    parser.add_argument("--value", type=int, default=None)
    parser.add_argument("--safe-test", action="store_true",
                        help="Test sicuro: toggla display (6,11) e verifica l'eco su /status/")
    parser.add_argument("--method", default="set_properties",
                        help="Metodo MiOT (default set_properties). 'action' richiede --allow-action")
    parser.add_argument("--allow-action", action="store_true",
                        help="Permette method=action (PERICOLOSO: WiFi reset). Richiede conferma.")
    parser.add_argument("--listen-secs", type=int, default=6, help="Secondi di ascolto eco dopo publish")
    args = parser.parse_args()

    if args.method == "action" and not args.allow_action:
        print("ERROR: method=action bloccato. Le action possono resettare il WiFi del MF10.")
        print("       Usa --allow-action solo se sai cosa stai facendo.")
        sys.exit(1)
    if args.method == "action" and args.allow_action:
        c = input("⚠️  action via MQTT puo' resettare il WiFi. Digita 'esegui' per confermare: ").strip()
        if c != "esegui":
            print("Annullato.")
            sys.exit(0)

    uid, token, did, model, bind, region, display_val = asyncio.run(_bootstrap())
    host, _, port_s = bind.partition(":")
    port = int(port_s) if port_s else 19973
    suffix = f"{did}/{uid}/{model}/{region}/"
    status_topic = f"/status/{suffix}"

    # Determina cosa pubblicare
    if args.safe_test:
        if display_val is None:
            print("ERROR: impossibile leggere display (6,11) per il safe-test")
            sys.exit(1)
        siid, piid = 6, 11
        value = 0 if display_val == 1 else 1
        print(f"SAFE-TEST: display (6,11) {display_val} → {value} (toggle innocuo, reversibile)")
    else:
        if args.siid is None or args.piid is None or args.value is None:
            print("ERROR: fornire --siid --piid --value, oppure usa --safe-test")
            sys.exit(1)
        siid, piid, value = args.siid, args.piid, args.value

    prefixes = [args.topic] if args.topic else list(CANDIDATE_PREFIXES)
    payload = build_payload(did, siid, piid, value, args.method)

    print(f"Broker:    mqtts://{host}:{port}")
    print(f"Device:    {model}  did={did}")
    print(f"Comando:   {args.method} siid={siid} piid={piid} value={value}")
    print(f"Payload:   {payload}")
    print(f"Topic da provare: {[f'/{p}/{suffix}' for p in prefixes]}\n")

    echoes = []
    echo_lock = threading.Lock()

    client_id = "p_" + os.urandom(8).hex()
    client = mqtt.Client(client_id=client_id, clean_session=True)
    client.username_pw_set(uid, token)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    client.tls_set_context(ctx)

    connected = threading.Event()

    def on_connect(c, u, f, rc):
        if rc == 0:
            c.subscribe(status_topic)
            print(f"[{time.strftime('%H:%M:%S')}] CONNESSO, iscritto a /status/", flush=True)
            connected.set()
        else:
            print(f"CONNECT fallito rc={rc}", flush=True)

    def on_publish(c, u, mid):
        print(f"[{time.strftime('%H:%M:%S')}] PUBLISH confermato (mid={mid})", flush=True)

    def on_message(c, u, msg):
        ts = time.strftime("%H:%M:%S")
        try:
            data = json.loads(msg.payload.decode("utf-8", "replace"))
        except Exception:
            print(f"[{ts}] /status/ (non-JSON): {msg.payload[:120]!r}", flush=True)
            return
        params = data.get("data", {}).get("params", [])
        # evidenzia se la property che abbiamo settato compare
        hit = [p for p in params if p.get("siid") == siid and p.get("piid") == piid]
        with echo_lock:
            echoes.append((ts, hit, params))
        if hit:
            print(f"[{ts}] ⚡ ECO sulla property target: (siid={siid},piid={piid})={hit[0].get('value')}", flush=True)
        else:
            short = [(p.get('siid'), p.get('piid'), p.get('value')) for p in params][:6]
            print(f"[{ts}] /status/ properties_changed: {short}{'...' if len(params)>6 else ''}", flush=True)

    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_message = on_message

    client.connect(host, port, keepalive=60)
    client.loop_start()
    if not connected.wait(timeout=10):
        print("ERRORE: connessione non stabilita in 10s")
        sys.exit(1)

    # Pubblica su ogni topic candidato, con verifica eco tra uno e l'altro
    baseline = len(echoes)
    for prefix in prefixes:
        topic = f"/{prefix}/{suffix}"
        print(f"\n[{time.strftime('%H:%M:%S')}] >>> PUBLISH su {topic}", flush=True)
        info = client.publish(topic, payload, qos=0)
        # attesa breve per eco attribuibile a questo topic
        deadline = time.time() + (args.listen_secs if args.topic else 3)
        while time.time() < deadline:
            time.sleep(0.3)
            with echo_lock:
                new_hits = [e for e in echoes[baseline:] if e[1]]
            if new_hits:
                print(f"[{time.strftime('%H:%M:%S')}] ✅✅✅ TOPIC COMANDO TROVATO: {topic}", flush=True)
                print("    Il device ha riportato il cambio della property target su /status/.")
                client.loop_stop(); client.disconnect()
                return

    print(f"\n[{time.strftime('%H:%M:%S')}] Nessuna eco sulla property target dopo tutti i topic.")
    print("    Ascolto ancora qualche secondo per eventuali eco ritardate...")
    time.sleep(args.listen_secs)
    with echo_lock:
        hits = [e for e in echoes if e[1]]
    if hits:
        print(f"    Eco ritardata ricevuta: {hits[-1]}")
    else:
        print("    Nessuna eco. I topic provati non sembrano accettare il nostro publish,")
        print("    oppure il comando non e' un set_properties su questa property via MQTT.")
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
