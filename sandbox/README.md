# sandbox/

Local Home Assistant instance for testing the `dreame_mf10` integration
under development.

## What's in here

- [docker-compose.yml](docker-compose.yml) — runs the official HA image
  (`ghcr.io/home-assistant/home-assistant:stable`).
- [config/configuration.yaml](config/configuration.yaml) — minimal HA config
  with debug logging enabled for our domain. Committed as a seed.
- `config/` — HA's persistent state lives here. Everything except
  `configuration.yaml` is gitignored (db, .storage, logs, secrets).

The integration source (`custom_components/dreame_mf10/`) is **not copied**
into this folder — it is bind-mounted live from the repo root by the
compose file. Edit the integration files where they normally live; restart
the container to pick up changes.

## Requirements

- Docker Desktop (or Docker Engine + Compose v2) on macOS / Linux / Windows.
- Port `8123` free on the host.

## Usage

From the repo root:

```bash
# Start (first launch: ~30–60s for HA bootstrap)
docker compose -f sandbox/docker-compose.yml up -d

# Tail logs (filter to our integration only)
docker compose -f sandbox/docker-compose.yml logs -f homeassistant | grep dreame_mf10

# Restart after editing custom_components/dreame_mf10/ (HA does NOT
# hot-reload custom integrations — a full restart is required)
docker compose -f sandbox/docker-compose.yml restart homeassistant

# Stop
docker compose -f sandbox/docker-compose.yml down
```

Or from inside `sandbox/`:

```bash
docker compose up -d
docker compose logs -f homeassistant
docker compose restart homeassistant
docker compose down
```

Then open <http://localhost:8123> in a browser.

## First-run setup

1. HA's onboarding wizard runs once. Create a throwaway user (not your
   real Dreamehome user — they are separate).
2. Skip the "find devices" step (or let it run; the MF10 won't appear
   here because we haven't registered the integration yet).
3. **Settings → Devices & Services → Add Integration** → search
   **"Dreame MF10"**. If you don't see it, the bind mount didn't pick up
   the custom component — check that `sandbox/config/custom_components/dreame_mf10/manifest.json`
   exists inside the container (`docker compose exec homeassistant ls /config/custom_components/dreame_mf10`).
4. Enter your **real** Dreamehome credentials + region (default `eu`).

## What to watch in the logs

Looking for, in order:
1. `Setting up dreame_mf10` — HA detected the integration.
2. Config flow goes through without `invalid_auth` / `cannot_connect`.
3. `Dreame MF10 entry loaded (did=..., model=dreame.fan.u2519) — coordinator/platforms not yet wired`.

If you see `region 'ru' is unverified` warning — expected, harmless unless
you actually picked `ru`.

## Reset

```bash
docker compose -f sandbox/docker-compose.yml down
rm -rf sandbox/config/.storage sandbox/config/home-assistant_v2.db sandbox/config/home-assistant.log*
```

The next `docker compose up -d` will re-run onboarding.

## Security notes

- This sandbox accepts real Dreamehome credentials at first launch — they
  end up encrypted in `sandbox/config/.storage/core.config_entries`,
  which is gitignored. Do not commit `sandbox/config/.storage/`.
- The HA admin user you create here is local-only on `localhost:8123`,
  not exposed externally.
