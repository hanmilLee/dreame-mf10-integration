"""Sensor platform for the Dreame MF10 integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODEL_MF10
from .coordinator import MF10Coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MF10Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MF10TemperatureSensor(coordinator, entry.data.get("mac"))])


class MF10TemperatureSensor(CoordinatorEntity[MF10Coordinator], SensorEntity):
    """Ambient temperature sensor read from the MF10 (siid=3, piid=2)."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_has_entity_name = True

    def __init__(self, coordinator: MF10Coordinator, mac: str | None) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.did}_temperature"
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

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("temperature")
