"""Test mirato: il campo `from` nel payload sendCommand sblocca il power?

Scoperta da ioBroker.dreame (integrazione funzionante): il payload `sendCommand`
include un campo `from` dentro `data` che il nostro client NON manda:

    data: { did, id, method, params, from: <uid?> }

Questo script logga, legge il power state, poi prova a inviare comandi power
CON il campo `from` (= uid) e ne verifica l'effetto. Bypassa `_send_command`
per costruire il payload custom con `from`.

Env: DREAME_USERNAME, DREAME_PASSWORD, DREAME_REGION (default eu)

NON tocca azioni siid=2 aiid=1/2/3 (WiFi reset confermato). Testa solo
set_properties su (2,1) e, opzionalmente, action con aiid alti.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

_env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.isfile(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "custom_components", "dreame_mf10"))

import aiohttp

from dreame_cloud import DreameCloud  # type: ignore[import]


async def send_with_from(cloud, did, method, params, host, from_val):
    """Invia sendCommand con il campo `from` dentro data. Ritorna la risposta grezza."""
    await cloud._ensure_token()
    host_prefix = f"-{host.split('.')[0]}" if host else ""
    url = f"{cloud.api_url}/dreame-iot-com{host_prefix}/device/sendCommand"
    rid = 1000
    inner = {"did": str(did), "id": rid, "method": method, "params": params}
    if from_val is not None:
        inner["from"] = from_val
    payload = {"did": str(did), "id": rid, "data": inner}
    async with cloud._session.post(
        url, headers=cloud._auth_headers(), json=payload,
        timeout=aiohttp.ClientTimeout(total=15),
    ) as resp:
        return await resp.json(content_type=None)


async def read_power(cloud, did, host):
    r = await cloud.async_get_properties(did, [{"siid": 2, "piid": 1}], host=host)
    for p in r or []:
        if p.get("siid") == 2 and p.get("piid") == 1 and p.get("code", -1) == 0:
            return p.get("value")
    return None


async def main() -> None:
    username = os.environ.get("DREAME_USERNAME")
    password = os.environ.get("DREAME_PASSWORD")
    region = os.environ.get("DREAME_REGION", "eu")
    if not username or not password:
        print("ERROR: set DREAME_USERNAME e DREAME_PASSWORD")
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        cloud = DreameCloud(username, password, region, session)
        await cloud.async_login()
        uid = cloud._uid
        print(f"Login OK — uid={uid}")

        devices = await cloud.async_get_devices()
        device = next((d for d in devices if "u2519" in d.get("model", "")), devices[0])
        did = device["did"]
        host = device.get("bindDomain")
        print(f"Device: {device.get('model')}  did={did}  host={host}\n")

        before = await read_power(cloud, did, host)
        print(f"Power iniziale: {before} (1=on, 2=standby)\n")

        # Candidati di valore per `from`: uid, did, stringa vuota
        from_candidates = [uid, str(did), ""]

        target = 1 if before == 2 else 2  # se standby prova on, se on prova off
        print(f"Tentativo set_properties(2,1,value={target}) con vari `from`:\n")
        for fv in from_candidates:
            params = [{"did": str(did), "siid": 2, "piid": 1, "value": target}]
            resp = await send_with_from(cloud, did, "set_properties", params, host, fv)
            code = resp.get("code")
            print(f"  from={fv!r:20} → code={code}  {resp.get('msg','')[:40]}")
            await asyncio.sleep(1.5)
            now = await read_power(cloud, did, host)
            if now != before:
                print(f"\n  ✅✅✅  POWER CAMBIATO: {before} → {now}  (from={fv!r})")
                return
        print(f"\n  Power invariato dopo tutti i tentativi: {await read_power(cloud, did, host)}")
        print("  → il campo `from` da solo non sblocca il power via set_properties.")


if __name__ == "__main__":
    asyncio.run(main())
