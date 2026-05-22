"""The Dreame MF10 integration.

Milestone 0 / 1: config entry creation only. Coordinator and platforms
(fan/sensor/switch/etc.) will be wired in later milestones.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Dreame MF10 config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "did": entry.data.get("did"),
        "model": entry.data.get("model"),
    }
    _LOGGER.info(
        "Dreame MF10 entry loaded (did=%s, model=%s) — coordinator/platforms not yet wired",
        entry.data.get("did"),
        entry.data.get("model"),
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Dreame MF10 config entry."""
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True
