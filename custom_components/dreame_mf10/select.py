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
    MF10_BLADE_OSC_BOTH,
    MF10_BLADE_OSC_LEFT,
    MF10_BLADE_OSC_NONE,
    MF10_BLADE_OSC_RIGHT,
    MF10_OSC_BOTH_INDEPENDENT,
    MF10_OSC_BOTH_STAGGERED,
    MF10_OSC_BOTH_SYNCHRONIZED,
    MF10_OSC_LEFT,
    MF10_OSC_OFF,
    MF10_OSC_OPTIONS,
    MF10_OSC_RIGHT,
    MF10_OSC_TO_PROPS,
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
    async_add_entities([MF10OscillationSelect(coordinator, mac)])


class MF10OscillationSelect(CoordinatorEntity[MF10Coordinator], SelectEntity):
    """Unified oscillation control.

    Composes blade_oscillation (2,6) with sync (2,11) and staggered (2,12).
    sync/staggered are only valid with both blades active, so this entity
    enforces coherent state transitions on writes.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "oscillation"
    _attr_icon = "mdi:rotate-3d-variant"
    _attr_options = MF10_OSC_OPTIONS

    def __init__(self, coordinator: MF10Coordinator, mac: str | None) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{coordinator.did}_oscillation"

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

    @property
    def current_option(self) -> str | None:
        blade = self.coordinator.data.get("blade_oscillation")
        if blade is None:
            return None
        if blade == MF10_BLADE_OSC_NONE:
            return MF10_OSC_OFF
        if blade == MF10_BLADE_OSC_LEFT:
            return MF10_OSC_LEFT
        if blade == MF10_BLADE_OSC_RIGHT:
            return MF10_OSC_RIGHT
        if blade == MF10_BLADE_OSC_BOTH:
            sync = self.coordinator.data.get("sync_oscillation") or 0
            staggered = self.coordinator.data.get("staggered_oscillation") or 0
            if sync:
                return MF10_OSC_BOTH_SYNCHRONIZED
            if staggered:
                return MF10_OSC_BOTH_STAGGERED
            return MF10_OSC_BOTH_INDEPENDENT
        return None

    async def async_select_option(self, option: str) -> None:
        if option not in MF10_OSC_TO_PROPS:
            raise HomeAssistantError(f"Unknown oscillation option: {option}")
        blade, sync, staggered = MF10_OSC_TO_PROPS[option]
        bp = MF10_PROPERTY_MAP["blade_oscillation"]
        sp = MF10_PROPERTY_MAP["sync_oscillation"]
        stp = MF10_PROPERTY_MAP["staggered_oscillation"]
        await self.coordinator.async_set_properties(
            [
                {"siid": bp["siid"], "piid": bp["piid"], "value": blade},
                {"siid": sp["siid"], "piid": sp["piid"], "value": sync},
                {"siid": stp["siid"], "piid": stp["piid"], "value": staggered},
            ]
        )
        await self.coordinator.async_request_refresh()
