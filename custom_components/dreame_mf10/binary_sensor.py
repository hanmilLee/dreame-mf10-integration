"""Binary sensor platform for the Dreame MF10 integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MF10_POWER_ON, MODEL_MF10
from .coordinator import MF10Coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MF10Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MF10PowerStateBinarySensor(coordinator, entry.data.get("mac"))])


class MF10PowerStateBinarySensor(CoordinatorEntity[MF10Coordinator], BinarySensorEntity):
    """Read-only power state (siid=2, piid=1). 1 = ON, 2 = standby."""

    _attr_has_entity_name = True
    _attr_translation_key = "power_state"
    _attr_device_class = BinarySensorDeviceClass.POWER

    def __init__(self, coordinator: MF10Coordinator, mac: str | None) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{coordinator.did}_power_state"

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
    def is_on(self) -> bool | None:
        power = self.coordinator.data.get("power")
        if power is None:
            return None
        return power == MF10_POWER_ON
