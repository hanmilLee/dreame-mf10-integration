#!/usr/bin/env python3
"""Scan MiOT properties on a Dreame MF10 via the Dreame Cloud.

Standalone CLI used to discover the device's real `(siid, piid)` property
map. Output is a JSON snapshot under `research/snapshots/` that can be
diffed with another snapshot (see `tools/diff_properties.py`) to identify
which properties change when a specific function is toggled from the
Dreamehome app.

Usage (from repo root):

    export DREAME_USERNAME='you@example.com'
    export DREAME_PASSWORD='hunter2'
    python tools/scan_properties.py --label before-speed-change --did <DID>

Run without `--did` to list the devices on the account.

Security:
    - Credentials are taken from env vars only (never argv).
    - Tokens, refresh tokens and auth headers are NEVER written to the
      snapshot. Only the property scan results, plus harmless metadata
      (model, did, region, timestamps, scan params).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Import dreame_cloud + const directly from the integration folder,
# bypassing custom_components/dreame_mf10/__init__.py (which pulls in
# the Home Assistant runtime — not available when running the CLI
# standalone outside HA).
_REPO_ROOT = Path(__file__).resolve().parent.parent
_PKG_DIR = _REPO_ROOT / "custom_components" / "dreame_mf10"
if str(_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(_PKG_DIR))

import aiohttp  # noqa: E402

from dreame_cloud import (  # noqa: E402
    DreameApiError,
    DreameAuthError,
    DreameCloud,
    DreameConnectionError,
)
from const import (  # noqa: E402
    DEFAULT_REGION,
    MF10_PROPERTY_CANDIDATES,
    REGION_OPTIONS,
    SUPPORTED_MODELS,
)

_LOG = logging.getLogger("scan_properties")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Scan MiOT (siid, piid) properties on a Dreame MF10."
    )
    p.add_argument(
        "--label",
        required=True,
        help="Short slug describing this snapshot (e.g. 'before-speed-change'). "
             "Used in the output filename.",
    )
    p.add_argument("--did", help="Device ID to scan. Omit to list devices and exit.")
    p.add_argument(
        "--region", default=DEFAULT_REGION, choices=REGION_OPTIONS,
        help=f"Dreame cloud region (default: {DEFAULT_REGION}).",
    )
    p.add_argument(
        "--candidates-only", action="store_true",
        help="Scan only the (siid, piid) listed in MF10_PROPERTY_CANDIDATES "
             "(fast, ~11 properties). Recommended mode — Dreame rejects whole "
             "batches when one property is unknown AND ~8s/request for unknowns, "
             "so a full range scan is impractical.",
    )
    p.add_argument("--siid-min", type=int, default=1)
    p.add_argument("--siid-max", type=int, default=10)
    p.add_argument("--piid-min", type=int, default=1)
    p.add_argument("--piid-max", type=int, default=30)
    p.add_argument(
        "--batch-size", type=int, default=1,
        help="Properties per get_properties call. Default 1: Dreame rejects "
             "entire envelopes when any property is unknown, so each request "
             "must contain only one to isolate failures.",
    )
    p.add_argument(
        "--batch-delay-ms", type=int, default=200,
        help="Pause between batches in milliseconds (default: 200).",
    )
    p.add_argument("--output", help="Output path (default: research/snapshots/<ts>-<label>.json).")
    p.add_argument("-v", "--verbose", action="store_true", help="Show MAC + DEBUG logs.")
    return p.parse_args()


def _default_output_path(label: str) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in label)[:64]
    return _REPO_ROOT / "research" / "snapshots" / f"{ts}-{safe}.json"


def _print_device_list(devices: list[dict[str, Any]], verbose: bool) -> None:
    print("Devices on account:")
    if not devices:
        print("  (none)")
        return
    for d in devices:
        model = d.get("model", "?")
        did = d.get("did", "?")
        name = d.get("deviceInfo", {}).get("deviceName") or d.get("name") or ""
        supported = " [SUPPORTED]" if model in SUPPORTED_MODELS else ""
        line = f"  did={did}  model={model}  name={name!r}{supported}"
        if verbose:
            mac = d.get("mac") or d.get("deviceInfo", {}).get("mac")
            if mac:
                line += f"  mac={mac}"
        print(line)


async def _preflight(cloud: DreameCloud, did: str, host: str | None) -> None:
    """Sanity-check using one known-good property.

    Power on a MiOT fan is conventionally (siid=2, piid=1) — we expect a
    list of length 1 with `code == 0`. If the item itself errors, the
    candidate is wrong (or this device doesn't expose it at all) and we
    don't want to burn ~8s on every property in the snapshot to discover
    that — abort early.
    """
    _LOG.info("Preflight: probing (siid=2, piid=1) to validate response.")
    try:
        res = await cloud.async_get_properties(did, [{"siid": 2, "piid": 1}], host=host)
    except DreameApiError as err:
        raise SystemExit(
            f"Preflight failed: backend rejected envelope ({err}). The base "
            "request path or auth is wrong — fix that before scanning."
        )
    if not isinstance(res, list) or not res:
        raise SystemExit(
            f"Preflight failed: expected non-empty list, got {res!r}."
        )
    code = res[0].get("code")
    if code != 0:
        _LOG.warning(
            "Preflight: (2,1) returned per-item code=%s — power may not live "
            "there on this model. Continuing scan, but expect some candidate "
            "entries to error similarly.",
            code,
        )
    else:
        _LOG.info("Preflight OK: (2,1) value=%r", res[0].get("value"))


def _classify_envelope_error(err: Exception) -> tuple[str, int | None]:
    """Extract a structured kind + optional envelope code from an exception."""
    if isinstance(err, DreameConnectionError):
        return "connection_error", None
    msg = str(err)
    code: int | None = None
    marker = "code="
    if marker in msg:
        try:
            code = int(msg.split(marker, 1)[1].split()[0].rstrip(","))
        except (ValueError, IndexError):
            code = None
    return "envelope_rejected", code


async def _scan(
    cloud: DreameCloud,
    did: str,
    host: str | None,
    targets: list[dict[str, int]],
    batch_size: int,
    batch_delay_s: float,
) -> list[dict[str, Any]]:
    total = len(targets)
    _LOG.info("Scanning %d properties (batch_size=%d).", total, batch_size)

    results: list[dict[str, Any]] = []
    for i in range(0, total, batch_size):
        batch = targets[i : i + batch_size]
        try:
            raw = await cloud.async_get_properties(did, batch, host=host)
        except (DreameApiError, DreameConnectionError) as err:
            kind, env_code = _classify_envelope_error(err)
            _LOG.warning(
                "Batch %d-%d %s (envelope_code=%s); marking items and continuing.",
                i, i + len(batch) - 1, kind, env_code,
            )
            for item in batch:
                results.append(
                    {
                        "siid": item["siid"],
                        "piid": item["piid"],
                        "code": None,
                        "error": {"kind": kind, "envelope_code": env_code, "message": str(err)},
                    }
                )
            await asyncio.sleep(batch_delay_s)
            continue

        for item, entry in zip(batch, raw):
            row: dict[str, Any] = {
                "siid": item["siid"],
                "piid": item["piid"],
                "code": entry.get("code"),
            }
            if "value" in entry:
                row["value"] = entry["value"]
            results.append(row)

        if (i // batch_size) % 10 == 0:
            _LOG.info("Progress: %d/%d", min(i + batch_size, total), total)
        await asyncio.sleep(batch_delay_s)

    return results


async def main_async(args: argparse.Namespace) -> int:
    username = os.environ.get("DREAME_USERNAME")
    password = os.environ.get("DREAME_PASSWORD")
    if not username or not password:
        print(
            "ERROR: set DREAME_USERNAME and DREAME_PASSWORD environment "
            "variables before running.",
            file=sys.stderr,
        )
        return 2

    async with aiohttp.ClientSession() as session:
        cloud = DreameCloud(username, password, args.region, session)
        try:
            await cloud.async_login()
        except DreameAuthError as err:
            print(f"Login rejected: {err}", file=sys.stderr)
            return 3
        except DreameConnectionError as err:
            print(f"Cannot reach Dreame Cloud: {err}", file=sys.stderr)
            return 4

        devices = await cloud.async_get_devices()

        if not args.did:
            _print_device_list(devices, args.verbose)
            print(
                "\nNo --did provided. Pick one from the list above and re-run with "
                "--did <DID>.",
                file=sys.stderr,
            )
            return 0

        target = next((d for d in devices if str(d.get("did")) == str(args.did)), None)
        if target is None:
            print(
                f"DID {args.did} not found on this account. Run without --did "
                "to see available devices.",
                file=sys.stderr,
            )
            return 5
        model = target.get("model", "")
        if model not in SUPPORTED_MODELS:
            _LOG.warning(
                "Model %r is not in SUPPORTED_MODELS. Scan will run anyway, but "
                "results may not be meaningful for this integration.",
                model,
            )
        host = target.get("bindDomain")
        if host:
            _LOG.info("Using bindDomain=%s for command routing.", host)
        else:
            _LOG.warning(
                "No bindDomain in device record; sendCommand will use the default "
                "path and may return HTTP 404. Run with -v to inspect the record."
            )

        await _preflight(cloud, args.did, host)

        if args.candidates_only:
            seen: set[tuple[int, int]] = set()
            targets: list[dict[str, int]] = []
            for entries in MF10_PROPERTY_CANDIDATES.values():
                for e in entries:
                    key = (e["siid"], e["piid"])
                    if key not in seen:
                        seen.add(key)
                        targets.append({"siid": key[0], "piid": key[1]})
            _LOG.info("Mode: candidates-only — %d unique (siid, piid) probes.", len(targets))
            mode = "candidates"
        else:
            _LOG.warning(
                "Mode: range scan — Dreame returns ~8s/request for unknown "
                "properties, so siid %d..%d × piid %d..%d will take a long time. "
                "Use --candidates-only unless you really need this.",
                args.siid_min, args.siid_max, args.piid_min, args.piid_max,
            )
            targets = [
                {"siid": s, "piid": p}
                for s in range(args.siid_min, args.siid_max + 1)
                for p in range(args.piid_min, args.piid_max + 1)
            ]
            mode = "range"

        results = await _scan(
            cloud,
            args.did,
            host,
            targets,
            args.batch_size,
            args.batch_delay_ms / 1000.0,
        )

        snapshot = {
            "metadata": {
                "model": model,
                "did": str(args.did),
                "region": args.region,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "scan_params": {
                    "mode": mode,
                    "siid_min": args.siid_min,
                    "siid_max": args.siid_max,
                    "piid_min": args.piid_min,
                    "piid_max": args.piid_max,
                    "batch_size": args.batch_size,
                    "batch_delay_ms": args.batch_delay_ms,
                },
                "label": args.label,
            },
            "results": results,
        }

        out_path = Path(args.output) if args.output else _default_output_path(args.label)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False))
        ok = sum(1 for r in results if r.get("code") == 0)
        print(f"Saved {len(results)} entries ({ok} with code=0) → {out_path}")
    return 0


def main() -> int:
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        return asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
