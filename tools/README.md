# tools/

Standalone CLI utilities for the Dreame MF10 integration. Run from the
**repo root** (they `sys.path`-inject the repo so they can import
`custom_components.dreame_mf10.dreame_cloud`).

## Requirements

- Python 3.11+
- `aiohttp` (`pip install aiohttp`)
- Credentials exposed as env vars — **never** as CLI arguments:

  ```bash
  export DREAME_USERNAME='you@example.com'
  export DREAME_PASSWORD='hunter2'
  ```

## `scan_properties.py`

Scan every `(siid, piid)` in a range on a target device and save a JSON
snapshot under `research/snapshots/`.

```bash
# 1) List devices on the account (no scan)
python tools/scan_properties.py --label list

# 2) Full scan of the MF10
python tools/scan_properties.py \
    --label before-speed-change \
    --did -115387050 \
    --region eu
```

Useful flags:

- `--siid-min / --siid-max` (default 1..10) — siid range to walk.
- `--piid-min / --piid-max` (default 1..30) — piid range to walk.
- `--batch-size` — **default 1**. Each property is fetched in its own
  request, so a single invalid piid doesn't poison the rest of the
  batch. Once you've confirmed empirically that Dreame returns
  per-property errors *inside* a successful envelope, you can raise it
  (e.g. `--batch-size 10`) to make the scan ~10× faster.
- `--batch-delay-ms` (default 200) — sleep between requests; keep > 0 to
  avoid tripping rate limiting.
- `-v` — verbose logs and reveal MAC in the device list (default hides it).

The output filename is `research/snapshots/<UTC-timestamp>-<label>.json`,
e.g. `2026-05-22-160230-before-speed-change.json`.

### Snapshot shape

```json
{
  "metadata": {
    "model": "dreame.fan.u2519",
    "did": "-115387050",
    "region": "eu",
    "timestamp_utc": "2026-05-22T16:02:30.123456+00:00",
    "scan_params": { "siid_min": 1, "siid_max": 10, "piid_min": 1, "piid_max": 30, "batch_size": 1, "batch_delay_ms": 200 },
    "label": "before-speed-change"
  },
  "results": [
    { "siid": 2, "piid": 1, "code": 0, "value": true },
    { "siid": 2, "piid": 99, "code": -704042011 }
  ]
}
```

Snapshots are **gitignored by default** (see [.gitignore](../.gitignore));
the only committed ones are `example.json` files in
[research/snapshots/](../research/snapshots/).

## `diff_properties.py`

Compare two snapshots and report only the properties whose `value`
changed. By default ignores entries that errored in either snapshot.

```bash
python tools/diff_properties.py before.json after.json
python tools/diff_properties.py before.json after.json --json     # machine-readable
python tools/diff_properties.py before.json after.json --include-errors
```

## Workflow: discover which property a function maps to

1. Note the current state of the device from the Dreamehome app.
2. `python tools/scan_properties.py --label before-<change> --did <DID>`.
3. Change **one** thing from the Dreamehome app (e.g. press the speed +
   button).
4. `python tools/scan_properties.py --label after-<change> --did <DID>`.
5. `python tools/diff_properties.py research/snapshots/<before>.json research/snapshots/<after>.json`.
6. The diff usually shows 1–2 changed `(siid, piid)` pairs. Those are
   the property you just toggled.
7. Repeat for a second cycle to rule out noise (e.g. a temperature
   sensor that drifts on its own).
8. Record the finding in [docs/property_map.md](../docs/property_map.md)
   (create it when the first property is confirmed).

## Security notes

- The snapshot JSON contains the device `did` (and the response shape
  from `listV2` may include other metadata). Treat snapshots as
  potentially-sensitive: do not commit raw snapshots to the public repo.
- Tokens, refresh tokens, and any Authorization headers are NEVER
  written to disk — only the property scan results and the metadata
  block above.
- If you share a snapshot publicly (e.g. for a bug report), redact the
  `did` and `region` fields manually first.
