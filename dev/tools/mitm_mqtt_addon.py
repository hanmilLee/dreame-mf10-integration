r"""Addon mitmproxy: decodifica i pacchetti MQTT dal flusso TCP decifrato.

Usato per catturare il comando power dell'app Dreamehome verso il broker MQTT
(10000.mt.eu.iot.dreame.tech:19973), che il proxy HTTP non vede.

mitmproxy fa TLS-decrypt del flusso (i broker MQTT in tcp_hosts) ed emette
`tcp_message`; qui bufferizziamo per-flow e parsiamo i pacchetti MQTT.

Interessano soprattutto i PUBLISH dal client (app→broker): topic + payload =
il comando esatto da replicare.

Avvio (vedi tools/mitm_run.sh):
    mitmdump --mode wireguard \
        --tcp-hosts 'mt\.eu\.iot\.dreame\.tech' \
        --set client_certs=tmp/dreamehome-apk/certs/client-combined.pem \
        -s tools/mitm_mqtt_addon.py

Output anche su file: tmp/mqtt_capture.log
"""

from __future__ import annotations

import os
import time

LOGFILE = os.path.join(os.path.dirname(__file__), "..", "..", "tmp", "mqtt_capture.log")

# MQTT control packet types (high nibble del primo byte)
PKT = {1: "CONNECT", 2: "CONNACK", 3: "PUBLISH", 4: "PUBACK", 8: "SUBSCRIBE",
       9: "SUBACK", 10: "UNSUBSCRIBE", 12: "PINGREQ", 13: "PINGRESP", 14: "DISCONNECT"}

# Buffer per flow (id connessione) e direzione
_buffers: dict = {}


def _log(line: str):
    ts = time.strftime("%H:%M:%S")
    msg = f"[{ts}] {line}"
    print(msg, flush=True)
    try:
        with open(LOGFILE, "a") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def _read_varint(buf, i):
    """Legge il Remaining Length MQTT (varint). Ritorna (valore, nuovo_indice) o (None, i)."""
    mult = 1
    val = 0
    for _ in range(4):
        if i >= len(buf):
            return None, i
        b = buf[i]
        i += 1
        val += (b & 0x7F) * mult
        if not (b & 0x80):
            return val, i
        mult *= 128
    return None, i


def _parse_packets(buf: bytearray, direction: str):
    """Estrae pacchetti MQTT completi dal buffer. Ritorna il buffer residuo."""
    while len(buf) >= 2:
        ptype = (buf[0] >> 4) & 0x0F
        flags = buf[0] & 0x0F
        rem, idx = _read_varint(buf, 1)
        if rem is None:
            break  # header incompleto
        total = idx + rem
        if len(buf) < total:
            break  # pacchetto incompleto, aspetta altri byte
        body = bytes(buf[idx:total])
        _handle_packet(ptype, flags, body, direction)
        del buf[:total]
    return buf


def _handle_packet(ptype, flags, body, direction):
    name = PKT.get(ptype, f"type{ptype}")
    arrow = "APP→broker" if direction == "c2s" else "broker→APP"

    if ptype == 3:  # PUBLISH
        if len(body) < 2:
            return
        tlen = (body[0] << 8) | body[1]
        topic = body[2:2 + tlen].decode("utf-8", "replace")
        rest = body[2 + tlen:]
        qos = (flags >> 1) & 0x03
        if qos > 0 and len(rest) >= 2:
            rest = rest[2:]  # salta packet identifier
        payload = rest.decode("utf-8", "replace")
        _log(f"⚡ PUBLISH [{arrow}] qos={qos}")
        _log(f"   TOPIC:   {topic}")
        _log(f"   PAYLOAD: {payload}")
    elif ptype == 1:  # CONNECT — estrai clientId, username, password
        try:
            i = 0
            plen = (body[i] << 8) | body[i + 1]; i += 2
            proto = body[i:i + plen].decode("utf-8", "replace"); i += plen
            i += 1  # protocol level
            cflags = body[i]; i += 1
            i += 2  # keepalive
            def _str(b, j):
                ln = (b[j] << 8) | b[j + 1]
                return b[j + 2:j + 2 + ln].decode("utf-8", "replace"), j + 2 + ln
            cid, i = _str(body, i)
            user = pwd = None
            if cflags & 0x04:  # will
                wt, i = _str(body, i); wp, i = _str(body, i)
            if cflags & 0x80:  # username
                user, i = _str(body, i)
            if cflags & 0x40:  # password
                pwd, i = _str(body, i)
            _log(f"CONNECT [{arrow}] proto={proto} clientId={cid} user={user} pass={('<'+str(len(pwd))+' char>') if pwd else None}")
        except Exception as ex:
            _log(f"CONNECT [{arrow}] ({len(body)} byte) parse-err {ex}")
    elif ptype == 8:  # SUBSCRIBE — estrai i topic filter
        try:
            i = 2  # packet identifier
            topics = []
            while i < len(body):
                ln = (body[i] << 8) | body[i + 1]; i += 2
                topics.append(body[i:i + ln].decode("utf-8", "replace")); i += ln
                i += 1  # qos
            _log(f"SUBSCRIBE [{arrow}] topics={topics}")
        except Exception as ex:
            _log(f"SUBSCRIBE [{arrow}] ({len(body)} byte) parse-err {ex}")
    elif ptype in (4, 9, 2, 12, 13):
        pass  # ack/ping rumorosi, ignora
    else:
        _log(f"{name} [{arrow}] ({len(body)} byte)")


# ── Hook mitmproxy ──────────────────────────────────────────────────────

def tcp_start(flow):
    _log(f"=== TCP flow aperto verso {flow.server_conn.address} ===")


def tcp_message(flow):
    msg = flow.messages[-1]
    direction = "c2s" if msg.from_client else "s2c"
    key = (id(flow), direction)
    buf = _buffers.setdefault(key, bytearray())
    buf += msg.content
    _buffers[key] = _parse_packets(buf, direction)


def tcp_end(flow):
    for d in ("c2s", "s2c"):
        _buffers.pop((id(flow), d), None)


def request(flow):
    """Logga i comandi REST sendCommand (per PATH, qualsiasi host — anche IP-based)."""
    try:
        path = (flow.request.path or "").lower()
        host = flow.request.host or ""
        # match per path: l'app usa endpoint IP-based, non hostname dreame
        if "sendcommand" in path or "/device/" in path or "dreame-iot" in path:
            method = flow.request.method
            body = flow.request.get_text() or ""
            _log(f"🌐🌐 COMANDO REST {method} {host}{flow.request.path}")
            _log(f"   REQ BODY: {body}")
    except Exception as ex:
        _log(f"HTTP request hook err: {ex}")


def response(flow):
    """Logga la risposta dei comandi sendCommand."""
    try:
        path = (flow.request.path or "").lower()
        if "sendcommand" in path or "dreame-iot" in path:
            rbody = flow.response.get_text() or ""
            _log(f"   RESP [{flow.response.status_code}]: {rbody[:400]}")
    except Exception as ex:
        _log(f"HTTP response hook err: {ex}")
