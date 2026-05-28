"""Number platform for the Dreame MF10 integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MF10_OFF_TIMER_MAX,
    MF10_OFF_TIMER_MIN,
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
    async_add_entities([MF10OffTimerNumber(coordinator, entry.data.get("mac"))])


class MF10OffTimerNumber(CoordinatorEntity[MF10Coordinator], NumberEntity):
    """Auto-off timer in hours (siid=2, piid=8). 0 = disabled."""

    _attr_has_entity_name = True
    _attr_translation_key = "off_timer"
    _attr_icon = "mdi:timer-outline"
    _attr_native_min_value = MF10_OFF_TIMER_MIN
    _attr_native_max_value = MF10_OFF_TIMER_MAX
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = UnitOfTime.HOURS

    def __init__(self, coordinator: MF10Coordinator, mac: str | None) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{coordinator.did}_off_timer"

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
    def native_value(self) -> float | None:
        val = self.coordinator.data.get("off_timer")
        if val is None:
            return None
        return float(val)

    async def async_set_native_value(self, value: float) -> None:
        p = MF10_PROPERTY_MAP["off_timer"]
        await self.coordinator.async_set_properties(
            [{"siid": p["siid"], "piid": p["piid"], "value": int(value)}]
        )
        await self.coordinator.async_request_refresh()
