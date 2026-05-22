#!/usr/bin/env python3
"""Diff two property snapshots produced by `scan_properties.py`.

Reports only `(siid, piid)` entries whose `value` changed between the two
snapshots. Entries that errored (code != 0) in either snapshot are skipped
unless `--include-errors` is passed.

Usage:

    python tools/diff_properties.py before.json after.json
    python tools/diff_properties.py before.json after.json --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as err:
        raise SystemExit(f"Cannot read {path}: {err}")
    if "results" not in data or not isinstance(data["results"], list):
        raise SystemExit(f"{path} doesn't look like a scan snapshot (missing 'results' list).")
    return data


def _index(snapshot: dict[str, Any]) -> dict[tuple[int, int], dict[str, Any]]:
    return {
        (r["siid"], r["piid"]): r
        for r in snapshot["results"]
        if "siid" in r and "piid" in r
    }


def _diff(
    before: dict[tuple[int, int], dict[str, Any]],
    after: dict[tuple[int, int], dict[str, Any]],
    include_errors: bool,
) -> list[dict[str, Any]]:
    keys = sorted(set(before) | set(after))
    out: list[dict[str, Any]] = []
    for key in keys:
        b = before.get(key)
        a = after.get(key)
        b_ok = b is not None and b.get("code") == 0
        a_ok = a is not None and a.get("code") == 0
        if not include_errors and not (b_ok and a_ok):
            continue
        b_val = b.get("value") if b else None
        a_val = a.get("value") if a else None
        if b_val == a_val and b_ok == a_ok:
            continue
        out.append(
            {
                "siid": key[0],
                "piid": key[1],
                "before": {"code": b.get("code") if b else None, "value": b_val},
                "after": {"code": a.get("code") if a else None, "value": a_val},
            }
        )
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Diff two property snapshots.")
    p.add_argument("before", type=Path)
    p.add_argument("after", type=Path)
    p.add_argument(
        "--include-errors", action="store_true",
        help="Show entries that errored in either snapshot too.",
    )
    p.add_argument("--json", action="store_true", help="JSON output to stdout.")
    args = p.parse_args()

    before = _load(args.before)
    after = _load(args.after)
    diff = _diff(_index(before), _index(after), args.include_errors)

    if args.json:
        json.dump(
            {
                "before_label": before.get("metadata", {}).get("label"),
                "after_label": after.get("metadata", {}).get("label"),
                "changes": diff,
            },
            sys.stdout,
            indent=2,
            ensure_ascii=False,
        )
        print()
        return 0

    if not diff:
        print("No changes between snapshots.")
        return 0

    b_lbl = before.get("metadata", {}).get("label", args.before.name)
    a_lbl = after.get("metadata", {}).get("label", args.after.name)
    print(f"Changes: {b_lbl} → {a_lbl}")
    for row in diff:
        s, p_id = row["siid"], row["piid"]
        bv, av = row["before"]["value"], row["after"]["value"]
        bc, ac = row["before"]["code"], row["after"]["code"]
        marker = "" if bc == 0 and ac == 0 else f"  (code {bc}→{ac})"
        print(f"  siid={s:>2} piid={p_id:>2} : {bv!r} → {av!r}{marker}")
    print(f"\nTotal: {len(diff)} change(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
