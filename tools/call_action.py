"""CLI tool for testing MiOT actions, set_properties e get_properties sul Dreame MF10.

Usage:
    # Leggi una property (es. power state siid=2, piid=1)
    python tools/call_action.py --read-prop --siid 2 --piid 1

    # Toggle power (legge stato, chiama action 2/3, ri-legge stato — mostra diff)
    python tools/call_action.py --toggle-power

    # Chiama una action generica (richiede conferma interattiva)
    python tools/call_action.py --siid 2 --aiid 3
    python tools/call_action.py --siid 2 --aiid 3 --params '[]'

    # Test set_properties (nessuna conferma richiesta)
    python tools/call_action.py --set-prop --siid 2 --piid 4 --value 3

Env vars required: DREAME_USERNAME, DREAME_PASSWORD
Optional:         DREAME_REGION (default: eu)

WARNING: actions e scritture di property possono cambiare lo stato del device fisico.
Usare solo per test espliciti.

AZIONI PERICOLOSE CONFERMATE (dreame.fan.u2519):
    siid=2, aiid=1 → reset WiFi del device (re-pairing richiesto) — confermato 2026-05-23
    siid=2, aiid=2 → reset WiFi del device (re-pairing richiesto) — confermato 2026-05-23
    siid=2, aiid=3 → reset WiFi del device (re-pairing richiesto) — confermato 2026-05-28
                     (NOTA: sul PM10/dreame.airp.* questa è il toggle power — NON sul MF10/fan)
    NON eseguire nessuna delle action siid=2 aiid=1/2/3 su questo modello.
    POWER STATE: siid=2, piid=1 — leggibile (1=on, 2=standby). Scrittura da testare con device ON.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys

# Load .env from project root if present (no external dependency)
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.isfile(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

# Import dreame_cloud directly (skips __init__.py which requires homeassistant)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "dreame_mf10"))

import aiohttp

from dreame_cloud import (  # type: ignore[import]
    DreameApiError,
    DreameAuthError,
    DreameCloud,
    DreameConnectionError,
)

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s %(message)s")


async def _read_power(cloud: "DreameCloud", did: str, host: str | None) -> int | None:
    """Legge siid=2, piid=1 (power state). Ritorna 1=on, 2=standby, None=errore."""
    result = await cloud.async_get_properties(did, [{"siid": 2, "piid": 1}], host=host)
    for prop in result or []:
        if prop.get("siid") == 2 and prop.get("piid") == 1 and prop.get("code", -1) == 0:
            return prop.get("value")
    return None


def _power_label(val: int | None) -> str:
    if val == 1:
        return "1 (ON)"
    if val == 2:
        return "2 (STANDBY)"
    return f"{val!r} (sconosciuto)"


async def main() -> None:
    parser = argparse.ArgumentParser(description="Test MiOT actions/properties sul Dreame MF10.")
    parser.add_argument("--siid", type=int, default=None, help="Service ID")
    parser.add_argument("--aiid", type=int, default=None, help="Action ID (per action calls)")
    parser.add_argument("--piid", type=int, default=None, help="Property ID (per --set-prop / --read-prop)")
    parser.add_argument("--value", type=str, default=None, help="Valore property come JSON (per --set-prop)")
    parser.add_argument("--set-prop", action="store_true", help="Usa set_properties invece di action")
    parser.add_argument("--read-prop", action="store_true", help="Leggi il valore corrente di siid/piid")
    parser.add_argument("--toggle-power", action="store_true",
                        help="Leggi power state → chiama action siid=2 aiid=3 → ri-leggi → mostra diff")
    parser.add_argument("--raw-method", type=str, default=None,
                        help="Invia un method MiOT/MIIO arbitrario (es. set_power, power_on)")
    parser.add_argument("--raw-params", type=str, default="[]",
                        help="JSON params per --raw-method (default: [])")
    parser.add_argument("--params", type=str, default="[]", help="JSON array di input params per action (default: [])")
    parser.add_argument("--region", type=str, default=None, help="Dreame region (default: DREAME_REGION env o eu)")
    args = parser.parse_args()

    # Validazioni
    if args.read_prop and (args.siid is None or args.piid is None):
        print("ERROR: --read-prop richiede --siid e --piid")
        sys.exit(1)
    if args.set_prop and (args.siid is None or args.piid is None or args.value is None):
        print("ERROR: --set-prop richiede --siid, --piid e --value")
        sys.exit(1)
    if args.raw_method is None and not args.read_prop and not args.set_prop and not args.toggle_power:
        if args.siid is None or args.aiid is None:
            print("ERROR: per action call fornire --siid e --aiid, oppure usa --read-prop / --set-prop / --toggle-power / --raw-method")
            sys.exit(1)

    # Conferma interattiva per action generiche (non --toggle-power che ha la propria)
    if not args.set_prop and not args.read_prop and not args.toggle_power and not args.raw_method:
        print(f"\n⚠️  ATTENZIONE: stai per eseguire l'action siid={args.siid} aiid={args.aiid}")
        print("   Le action possono cambiare lo stato fisico del device.")
        confirm = input("   Digita 'esegui' per confermare: ").strip()
        if confirm != "esegui":
            print("Operazione annullata.")
            sys.exit(0)

    username = os.environ.get("DREAME_USERNAME")
    password = os.environ.get("DREAME_PASSWORD")
    region = args.region or os.environ.get("DREAME_REGION", "eu")

    if not username or not password:
        print("ERROR: imposta DREAME_USERNAME e DREAME_PASSWORD come variabili d'ambiente")
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        cloud = DreameCloud(username, password, region, session)
        try:
            await cloud.async_login()
        except DreameAuthError as e:
            print(f"ERROR login: {e}")
            sys.exit(1)
        except DreameConnectionError as e:
            print(f"ERROR connection: {e}")
            sys.exit(1)

        devices = await cloud.async_get_devices()
        if not devices:
            print("ERROR: nessun device trovato sull'account")
            sys.exit(1)

        # Prendi MF10 (dreame.fan.u2519) o il primo device
        device = next((d for d in devices if "u2519" in d.get("model", "")), devices[0])
        did = device["did"]
        host = device.get("bindDomain")
        model = device.get("model", "unknown")
        print(f"\nDevice: {model}  did={did}  host={host}")

        try:
            if args.raw_method:
                try:
                    raw_params = json.loads(args.raw_params)
                except json.JSONDecodeError as e:
                    print(f"ERROR: --raw-params JSON non valido: {e}")
                    sys.exit(1)
                print(f"\nraw method: {args.raw_method!r}  params={raw_params}")
                # Bypassa _send_command (che lancia su code!=0) per vedere la risposta grezza
                await cloud._ensure_token()
                host_prefix = f"-{host.split('.')[0]}" if host else ""
                url = f"{cloud.api_url}/dreame-iot-com{host_prefix}/device/sendCommand"
                payload = {
                    "did": str(did),
                    "id": 1,
                    "data": {"did": str(did), "id": 1, "method": args.raw_method, "params": raw_params},
                }
                import aiohttp as _aiohttp
                async with session.post(url, headers=cloud._auth_headers(), json=payload,
                                        timeout=_aiohttp.ClientTimeout(total=15)) as resp:
                    body = await resp.json(content_type=None)
                print(f"HTTP {resp.status}")
                print(json.dumps(body, indent=2, ensure_ascii=False))

            elif args.toggle_power:
                # BLOCCATO: siid=2 aiid=3 causa reset WiFi sul MF10 (dreame.fan.u2519).
                # Non è toggle power — è un'azione di reset. Confermato 2026-05-28.
                # Rimuovere questo blocco solo dopo aver identificato l'action corretta per il MF10.
                print("\n❌  --toggle-power BLOCCATO")
                print("    siid=2, aiid=3 causa reset WiFi sul MF10 (dreame.fan.u2519).")
                print("    Non corrisponde al toggle power del PM10.")
                print("    Identifica prima l'action corretta, poi aggiorna questo blocco.")
                sys.exit(1)

            elif args.read_prop:
                print(f"\nLettura siid={args.siid}, piid={args.piid}...")
                result = await cloud.async_get_properties(
                    did, [{"siid": args.siid, "piid": args.piid}], host=host
                )
                print(f"Result: {result}")
                for prop in result or []:
                    if prop.get("code", -1) == 0:
                        print(f"\n✅  siid={prop['siid']} piid={prop['piid']} = {prop['value']!r} ({type(prop['value']).__name__})")
                    else:
                        print(f"\n❌  code={prop.get('code')} (property non leggibile o non esistente)")

            elif args.set_prop:
                value = json.loads(args.value)
                prop = [{"siid": args.siid, "piid": args.piid, "value": value}]
                print(f"\nset_properties: siid={args.siid} piid={args.piid} value={value}")
                result = await cloud.async_set_properties(did, prop, host=host)
                print(f"Result: {result}")

            else:
                try:
                    params = json.loads(args.params)
                except json.JSONDecodeError as e:
                    print(f"ERROR: --params JSON non valido: {e}")
                    sys.exit(1)
                print(f"\naction: siid={args.siid} aiid={args.aiid} params={params}")
                result = await cloud.async_call_action(did, args.siid, args.aiid, params=params, host=host)
                print(f"Result: {result}")

        except DreameApiError as e:
            print(f"API error: {e}")
        except DreameConnectionError as e:
            print(f"Connection error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
