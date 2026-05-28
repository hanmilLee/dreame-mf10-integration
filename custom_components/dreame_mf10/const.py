"""Constants for the Dreame MF10 integration."""

from __future__ import annotations

DOMAIN = "dreame_mf10"

MODEL_MF10 = "dreame.fan.u2519"
SUPPORTED_MODELS = {MODEL_MF10}

CONF_REGION = "region"
CONF_POLLING_INTERVAL = "polling_interval"
CONF_DEBUG_PROPERTY_SCAN = "debug_property_scan"
CONF_EXPERIMENTAL_ENTITIES = "experimental_entities"

REGION_OPTIONS = ["eu", "cn", "us", "sg", "ru"]
DEFAULT_REGION = "eu"

DEFAULT_POLLING_INTERVAL = 30
MIN_POLLING_INTERVAL = 10
MAX_POLLING_INTERVAL = 300

MF10_SPEED_MIN = 1
MF10_SPEED_MAX = 10

PLATFORMS: list[str] = ["sensor", "fan"]

MF10_POWER_ON = 1
MF10_POWER_OFF = 2

# Provisional MiOT property candidates for dreame.fan.u2519.
# These are NOT validated — they must be confirmed via discovery (tools/scan_properties.py)
# before being promoted into MF10_PROPERTY_MAP.
MF10_PROPERTY_CANDIDATES: dict[str, list[dict[str, int]]] = {
    # Confirmed (see docs/property_map.md)
    "power": [{"siid": 2, "piid": 1}],
    "mode": [{"siid": 2, "piid": 3}],
    "fan_speed": [{"siid": 2, "piid": 4}],
    "child_lock": [{"siid": 2, "piid": 5}],
    "temperature": [{"siid": 3, "piid": 2}],
    # Unconfirmed — oscillation and other controls
    "unknown_2_2": [{"siid": 2, "piid": 2}],
    "oscillation_candidates": [
        {"siid": 2, "piid": 7},
        {"siid": 2, "piid": 8},
        {"siid": 2, "piid": 10},
        {"siid": 2, "piid": 11},
        {"siid": 2, "piid": 12},
    ],
    "siid6_candidates": [
        {"siid": 6, "piid": 1},
        {"siid": 6, "piid": 2},
        {"siid": 6, "piid": 3},
        {"siid": 6, "piid": 4},
        {"siid": 6, "piid": 6},
        {"siid": 6, "piid": 7},
    ],
}

# Validated property map — populated from before/after diff discovery session
# 2026-05-22 on device dreame.fan.u2519 (did=-115387050, region=eu).
# These are the canonical (siid, piid) for production polling and entity state.
MF10_PROPERTY_MAP: dict[str, dict] = {
    "power": {"siid": 2, "piid": 1},              # 1=ON, 2=OFF — read-only
    "mode": {"siid": 2, "piid": 3},               # 0=AI auto, 1=Potente, 2=Sonno, 3=Manuale, 7=Naturale
    "fan_speed": {"siid": 2, "piid": 4},          # int 1–10
    "child_lock": {"siid": 2, "piid": 5},         # 0=OFF, 1=ON
    "blade_oscillation": {"siid": 2, "piid": 6},   # 0=none, 1=left, 2=right, 3=both
    "oscillation": {"siid": 2, "piid": 7},         # 0=OFF, 1=ON (master swing toggle)
    "sync_oscillation": {"siid": 2, "piid": 11},        # 0=off, 1=on (blades move in sync)
    "staggered_oscillation": {"siid": 2, "piid": 12},  # 0=off, 1=on (blades out of phase)
    "continuous_monitoring": {"siid": 2, "piid": 10},  # 0=off, 1=on (TempSync feature)
    "key_tone": {"siid": 6, "piid": 7},                # 0=off, 1=on (tono tasti / beep)
    "display": {"siid": 6, "piid": 11},               # 0=off, 1=on (display LED)
    "off_timer": {"siid": 2, "piid": 8},              # 0=disattivato, int=ore (timer spegnimento)
    "temperature": {"siid": 3, "piid": 2},              # °C, read-only sensor
}

# Properties discovered but NOT yet identified:
#   (2, 2) — always 0 across all modes and states
#   (2, 7) — always 0 across all oscillation tests; purpose unknown
#   (2, 8) — always 0
#   (2, 10) — always 1
#   (6, 4) — always 0
#   (6, 7) — always 1 (NOT child_lock; possibly buzzer or display)
# System read-only (not polled):
#   (6, 1) — timezone string e.g. "Europe/Rome"
#   (6, 2) — empty string (device name?)

# Blade oscillation enum values (for MF10_PROPERTY_MAP["blade_oscillation"])
MF10_BLADE_OSC_NONE = 0
MF10_BLADE_OSC_LEFT = 1
MF10_BLADE_OSC_RIGHT = 2
MF10_BLADE_OSC_BOTH = 3

# Fan mode enum values (for MF10_PROPERTY_MAP["mode"])
MF10_MODE_AI = 0
MF10_MODE_POWERFUL = 1
MF10_MODE_NIGHT = 2
MF10_MODE_MANUAL = 3
MF10_MODE_NATURAL = 7

MF10_MODE_OPTIONS: dict[int, str] = {
    MF10_MODE_AI: "ai",
    MF10_MODE_POWERFUL: "powerful",
    MF10_MODE_NIGHT: "night",
    MF10_MODE_MANUAL: "manual",
    MF10_MODE_NATURAL: "natural",
}
MF10_MODE_NAME_TO_VALUE: dict[str, int] = {v: k for k, v in MF10_MODE_OPTIONS.items()}
