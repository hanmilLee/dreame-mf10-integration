#!/usr/bin/env bash
# Avvia mitmproxy in modalità WireGuard per catturare il comando MQTT dell'app Dreamehome.
#
# Setup iPhone (una tantum):
#   1. Installa l'app "WireGuard" dall'App Store sull'iPhone.
#   2. Avvia questo script: stampa un QR code WireGuard.
#   3. WireGuard app → "+" → "Crea da QR code" → scansiona → attiva il tunnel.
#   4. Tutto il traffico dell'iPhone ora passa dal Mac via WireGuard (anche MQTT).
#   5. Cert mitmproxy: Safari iPhone → http://mitm.it → installa profilo iOS →
#      Impostazioni → Generali → VPN e gestione dispositivi → installa →
#      Impostazioni → Generali → Info → Impostazioni certificati → ABILITA trust.
#
# Cattura:
#   - Con tunnel attivo e cert trustato, apri l'app Dreamehome → pagina device → ON/OFF.
#   - I PUBLISH MQTT (app→broker) appaiono qui e in tmp/mqtt_capture.log.
#
# Se l'app fa pinning stretto sul cert del broker, la connessione MQTT fallira'
# (device "Disconnesso" nell'app) e non vedremo PUBLISH: in quel caso il MITM e' bloccato.

set -e
cd "$(dirname "$0")/../.."

CERT="tmp/dreamehome-apk/certs/client-combined.pem"

echo "Avvio mitmproxy (WireGuard). Scansiona il QR con l'app WireGuard sull'iPhone."
echo "Log MQTT: tmp/mqtt_capture.log"
echo ""

exec .venv/bin/mitmdump \
    --mode wireguard \
    --tcp-hosts 'mt\.eu\.iot\.dreame\.tech' \
    --set client_certs="$CERT" \
    --set connection_strategy=lazy \
    -s tools/mitm_mqtt_addon.py
