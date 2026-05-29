"""Subscriber MQTT al broker Dreame — osserva gli eventi del device in tempo reale.

Scopo (test diagnostico, suggerito dall'advisor):
  1. Conferma che il device emette `properties_changed` quando lo controlli dall'app.
  2. Iscrivendosi a `#` (tutto), verifica se QUALCHE comando viaggia su MQTT
     (l'ipotesi corrente, da ioBroker.dreame, è che MQTT sia solo ricezione e
     i comandi vadano via REST sendCommand).

Parametri di connessione (da ioBroker.dreame, codice in chiaro):
    broker:   mqtts://{bindDomain}          # es. 10000.mt.eu.iot.dreame.tech:19973
    clientId: p_<8 byte hex casuali>
    username: uid
    password: access_token
    rejectUnauthorized: false               # no verifica cert server, no cert client
    topic:    /status/{did}/{uid}/{model}/eu/

Uso:
    set -a; source .env; set +a
    python3 tools/mqtt_listen.py              # iscrizione al solo /status/ del device
    python3 tools/mqtt_listen.py --wildcard   # iscrizione a `#` (tutto — test advisor)

Env: DREAME_USERNAME, DREAME_PASSWORD, DREAME_REGION (default eu)

Premi ON/OFF dall'app Dreamehome mentre questo gira e osserva i topic/payload.
Ctrl+C per uscire.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import ssl
import sys
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


async def _bootstrap():
    """Login + lista device. Ritorna (uid, access_token, did, model, bindDomain)."""
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
        return (
            cloud._uid,
            cloud._access_token,
            str(device["did"]),
            device.get("model", ""),
            device.get("bindDomain"),
            region,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Subscriber MQTT broker Dreame")
    parser.add_argument("--wildcard", action="store_true",
                        help="Iscriviti a `#` (tutto) invece del solo /status/ del device")
    args = parser.parse_args()

    uid, token, did, model, bind, region = asyncio.run(_bootstrap())
    host, _, port_s = bind.partition(":")
    port = int(port_s) if port_s else 19973
    print(f"Broker:   mqtts://{host}:{port}")
    print(f"Device:   {model}  did={did}")
    print(f"uid:      {uid}")

    status_topic = f"/status/{did}/{uid}/{model}/{region}/"
    sub_topic = "#" if args.wildcard else status_topic
    print(f"Subscribe: {sub_topic}\n")

    # clientId deterministico ma unico (no Math.random nel sandbox; qui ok)
    client_id = "p_" + os.urandom(8).hex()

    client = mqtt.Client(client_id=client_id, clean_session=True)
    client.username_pw_set(uid, token)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # rejectUnauthorized: false
    client.tls_set_context(ctx)

    def on_connect(c, userdata, flags, rc):
        if rc == 0:
            print(f"[{time.strftime('%H:%M:%S')}] CONNESSO al broker")
            c.subscribe(sub_topic)
            print(f"[{time.strftime('%H:%M:%S')}] Iscritto a {sub_topic}")
            print("\n>>> Ora premi ON/OFF dall'app Dreamehome e osserva qui <<<\n")
        else:
            print(f"CONNECT fallito rc={rc} ({mqtt.connack_string(rc)})")

    def on_message(c, userdata, msg):
        ts = time.strftime("%H:%M:%S")
        try:
            payload = msg.payload.decode("utf-8", "replace")
        except Exception:
            payload = repr(msg.payload)
        print(f"[{ts}] TOPIC: {msg.topic}")
        print(f"         {payload}\n")

    def on_disconnect(c, userdata, rc):
        print(f"[{time.strftime('%H:%M:%S')}] DISCONNESSO rc={rc}")

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    try:
        client.connect(host, port, keepalive=60)
    except Exception as ex:
        print(f"ERRORE connessione: {ex}")
        sys.exit(1)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nUscita.")
        client.disconnect()


if __name__ == "__main__":
    main()
