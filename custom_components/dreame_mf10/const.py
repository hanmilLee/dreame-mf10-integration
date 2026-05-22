"""Constants for the Dreame MF10 integration."""

from __future__ import annotations

DOMAIN = "dreame_mf10"

MODEL_MF10 = "dreame.fan.u2519"
SUPPORTED_MODELS = {MODEL_MF10}

CONF_REGION = "region"
CONF_POLLING_INTERVAL = "polling_interval"
CONF_OFF_BEHAVIOR = "off_behavior"
CONF_DEBUG_PROPERTY_SCAN = "debug_property_scan"
CONF_EXPERIMENTAL_ENTITIES = "experimental_entities"

REGION_OPTIONS = ["eu", "cn", "us", "sg", "ru"]
DEFAULT_REGION = "eu"

DEFAULT_POLLING_INTERVAL = 30
MIN_POLLING_INTERVAL = 10
MAX_POLLING_INTERVAL = 300

OFF_BEHAVIOR_REAL = "real"
OFF_BEHAVIOR_SOFT = "soft"
OFF_BEHAVIOR_OPTIONS = [OFF_BEHAVIOR_REAL, OFF_BEHAVIOR_SOFT]
DEFAULT_OFF_BEHAVIOR = OFF_BEHAVIOR_REAL

MF10_SPEED_MIN = 1
MF10_SPEED_MAX = 10

# Provisional MiOT property candidates for dreame.fan.u2519.
# These are NOT validated — they must be confirmed via discovery (tools/scan_properties.py)
# before being promoted into MF10_PROPERTY_MAP.
MF10_PROPERTY_CANDIDATES: dict[str, list[dict[str, int]]] = {
    "power": [
        {"siid": 2, "piid": 1},
    ],
    "mode": [
        {"siid": 2, "piid": 2},
        {"siid": 2, "piid": 3},
    ],
    "speed": [
        {"siid": 2, "piid": 4},
        {"siid": 2, "piid": 5},
    ],
    "temperature": [
        {"siid": 3, "piid": 1},
        {"siid": 3, "piid": 2},
        {"siid": 3, "piid": 3},
    ],
    "display_light": [
        {"siid": 6, "piid": 5},
        {"siid": 6, "piid": 8},
    ],
    "child_lock": [
        {"siid": 6, "piid": 7},
    ],
}

# Validated property map — empty until discovery completes (Phase 2).
# An empty map means the coordinator should NOT poll properties yet; once
# entries are added here they become the authoritative source for polling
# and entity state, replacing MF10_PROPERTY_CANDIDATES in production code.
MF10_PROPERTY_MAP: dict[str, dict] = {}
