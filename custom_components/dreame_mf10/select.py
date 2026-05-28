"""Select platform for the Dreame MF10 integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MF10_BLADE_OSC_NAME_TO_VALUE,
    MF10_BLADE_OSC_OPTIONS,
    MF10_OSC_PATTERN_INDEPENDENT,
    MF10_OSC_PATTERN_STAGGERED,
    MF10_OSC_PATTERN_SYNCHRONIZED,
    MF10_OSC_PATTERNS,
    MF10_PROPERTY_MAP,
    MODEL_MF10,
)
from .coordinator import MF10Coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MF10Coordinator = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data.get("mac")
    async_add_entities(
        [
            MF10BladeOscillationSelect(coordinator, mac),
            MF10OscillationPatternSelect(coordinator, mac),
        ]
    )


class _MF10SelectBase(CoordinatorEntity[MF10Coordinator], SelectEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: MF10Coordinator, mac: str | None) -> None:
        super().__init__(coordinator)
        self._mac = mac

    @property
    def device_info(self) -> DeviceInfo:
        connections = (
            {(CONNECTION_NETWORK_MAC, self._mac)} if self._mac else set()
        )
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.did)},
            connections=connections,
            name="Dreame MF10",
            model=MODEL_MF10,
            manufacturer="Dreame",
        )


class MF10BladeOscillationSelect(_MF10SelectBase):
    """Blade oscillation: none / left / right / both (siid=2, piid=6)."""

    _attr_translation_key = "blade_oscillation"
    _attr_icon = "mdi:rotate-3d-variant"
    _attr_options = list(MF10_BLADE_OSC_OPTIONS.values())

    def __init__(self, coordinator: MF10Coordinator, mac: str | None) -> None:
        super().__init__(coordinator, mac)
        self._attr_unique_id = f"{coordinator.did}_blade_oscillation"

    @property
    def current_option(self) -> str | None:
        val = self.coordinator.data.get("blade_oscillation")
        if val is None:
            return None
        return MF10_BLADE_OSC_OPTIONS.get(val)

    async def async_select_option(self, option: str) -> None:
        value = MF10_BLADE_OSC_NAME_TO_VALUE.get(option)
        if value is None:
            raise HomeAssistantError(f"Unknown blade oscillation: {option}")
        p = MF10_PROPERTY_MAP["blade_oscillation"]
        await self.coordinator.async_set_properties(
            [{"siid": p["siid"], "piid": p["piid"], "value": value}]
        )
        await self.coordinator.async_request_refresh()


class MF10OscillationPatternSelect(_MF10SelectBase):
    """Oscillation pattern composed of sync_oscillation (2,11) + staggered_oscillation (2,12).

    The two underlying flags are mutually exclusive on the device. This select
    exposes them as a single tri-state to prevent inconsistent combinations.
    """

    _attr_translation_key = "oscillation_pattern"
    _attr_icon = "mdi:sine-wave"
    _attr_options = MF10_OSC_PATTERNS

    def __init__(self, coordinator: MF10Coordinator, mac: str | None) -> None:
        super().__init__(coordinator, mac)
        self._attr_unique_id = f"{coordinator.did}_oscillation_pattern"

    @property
    def current_option(self) -> str | None:
        sync = self.coordinator.data.get("sync_oscillation")
        staggered = self.coordinator.data.get("staggered_oscillation")
        if sync is None or staggered is None:
            return None
        if sync:
            return MF10_OSC_PATTERN_SYNCHRONIZED
        if staggered:
            return MF10_OSC_PATTERN_STAGGERED
        return MF10_OSC_PATTERN_INDEPENDENT

    async def async_select_option(self, option: str) -> None:
        if option not in MF10_OSC_PATTERNS:
            raise HomeAssistantError(f"Unknown oscillation pattern: {option}")
        sync = 1 if option == MF10_OSC_PATTERN_SYNCHRONIZED else 0
        staggered = 1 if option == MF10_OSC_PATTERN_STAGGERED else 0
        sp = MF10_PROPERTY_MAP["sync_oscillation"]
        stp = MF10_PROPERTY_MAP["staggered_oscillation"]
        await self.coordinator.async_set_properties(
            [
                {"siid": sp["siid"], "piid": sp["piid"], "value": sync},
                {"siid": stp["siid"], "piid": stp["piid"], "value": staggered},
            ]
        )
        await self.coordinator.async_request_refresh()
