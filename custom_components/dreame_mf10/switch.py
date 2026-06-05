"""Switch platform for the Dreame MF10 integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MF10_PROPERTY_MAP, MODEL_MF10
from .coordinator import MF10Coordinator


@dataclass(frozen=True)
class _SwitchSpec:
    key: str            # property key in MF10_PROPERTY_MAP
    translation_key: str
    icon: str | None = None


_SWITCHES: tuple[_SwitchSpec, ...] = (
    _SwitchSpec("child_lock", "child_lock", "mdi:lock"),
    _SwitchSpec("device_rotation", "device_rotation", "mdi:rotate-360"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MF10Coordinator = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data.get("mac")
    async_add_entities(
        MF10Switch(coordinator, mac, spec) for spec in _SWITCHES
    )


class MF10Switch(CoordinatorEntity[MF10Coordinator], SwitchEntity):
    """Generic on/off MiOT property switch (0=off, 1=on)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MF10Coordinator,
        mac: str | None,
        spec: _SwitchSpec,
    ) -> None:
        super().__init__(coordinator)
        self._spec = spec
        self._mac = mac
        self._attr_unique_id = f"{coordinator.did}_{spec.key}"
        self._attr_translation_key = spec.translation_key
        if spec.icon:
            self._attr_icon = spec.icon

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
        val = self.coordinator.data.get(self._spec.key)
        if val is None:
            return None
        return bool(val)

    async def _async_write(self, value: int) -> None:
        p = MF10_PROPERTY_MAP[self._spec.key]
        await self.coordinator.async_set_properties(
            [{"siid": p["siid"], "piid": p["piid"], "value": value}]
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_write(1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_write(0)
