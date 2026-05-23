"""CLI tool for testing MiOT actions and set_properties on the Dreame MF10.

Usage:
    # Test an action (aiid)
    python tools/call_action.py --siid 2 --aiid 3
    python tools/call_action.py --siid 2 --aiid 3 --params '[]'

    # Test set_properties for a specific property
    python tools/call_action.py --set-prop --siid 2 --piid 4 --value 3

Env vars required: DREAME_USERNAME, DREAME_PASSWORD
Optional:         DREAME_REGION (default: eu)

WARNING: actions and property writes can physically move the device (rotate
blades, change state, reset configuration). Use only for explicit testing.

KNOWN DANGEROUS ACTIONS (dreame.fan.u2519):
    siid=2, aiid=1 → code=0 ma causa reset WiFi del device (re-pairing richiesto)
    siid=2, aiid=2 → code=0 ma causa reset WiFi del device (re-pairing richiesto)
    NON richiamare queste action senza intenzione esplicita.
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


async def main() -> None:
    parser = argparse.ArgumentParser(description="Test a MiOT action on the Dreame MF10.")
    parser.add_argument("--siid", type=int, required=True, help="Service ID")
    parser.add_argument("--aiid", type=int, default=None, help="Action ID (for action calls)")
    parser.add_argument("--piid", type=int, default=None, help="Property ID (for --set-prop)")
    parser.add_argument("--value", type=str, default=None, help="Property value as JSON (for --set-prop)")
    parser.add_argument("--set-prop", action="store_true", help="Use set_properties instead of action")
    parser.add_argument("--params", type=str, default="[]", help='JSON array of input params for action (default: [])')
    parser.add_argument("--region", type=str, default=None, help="Dreame region (default: DREAME_REGION env or eu)")
    args = parser.parse_args()

    if args.set_prop and (args.piid is None or args.value is None):
        print("ERROR: --set-prop requires --piid and --value")
        sys.exit(1)
    if not args.set_prop and args.aiid is None:
        print("ERROR: provide --aiid for action call, or use --set-prop with --piid and --value")
        sys.exit(1)

    username = os.environ.get("DREAME_USERNAME")
    password = os.environ.get("DREAME_PASSWORD")
    region = args.region or os.environ.get("DREAME_REGION", "eu")

    if not username or not password:
        print("ERROR: set DREAME_USERNAME and DREAME_PASSWORD environment variables")
        sys.exit(1)

    try:
        params = json.loads(args.params)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid --params JSON: {e}")
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
            print("ERROR: no devices found on this account")
            sys.exit(1)

        # Pick the MF10 (dreame.fan.u2519) or the first device
        device = next((d for d in devices if "u2519" in d.get("model", "")), devices[0])
        did = device["did"]
        host = device.get("bindDomain")
        model = device.get("model", "unknown")
        print(f"\nDevice: {model}  did={did}  host={host}")
        print(f"Calling action: siid={args.siid}  aiid={args.aiid}  params={params}\n")

        try:
            if args.set_prop:
                value = json.loads(args.value)
                prop = [{"siid": args.siid, "piid": args.piid, "value": value}]
                print(f"Calling set_properties: siid={args.siid} piid={args.piid} value={value}\n")
                result = await cloud.async_set_properties(did, prop, host=host)
            else:
                params = json.loads(args.params)
                print(f"Calling action: siid={args.siid} aiid={args.aiid} params={params}\n")
                result = await cloud.async_call_action(did, args.siid, args.aiid, params=params, host=host)
            print(f"Result: {result}")
        except DreameApiError as e:
            print(f"API error: {e}")
        except DreameConnectionError as e:
            print(f"Connection error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
