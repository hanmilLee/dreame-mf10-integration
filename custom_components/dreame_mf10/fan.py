"""Fan platform for the Dreame MF10 integration.

Power on/off is performed via MiOT action siid=2 aiid=1 (input piid=1, value 1/0),
validated 2026-05-29 against the real device. The power property (2,1) itself is
read-only; the older "niente fan.py — turn_on/off non supportabile" rationale is
obsolete now that the action-based toggle is known.

Fan speed (siid=2, piid=4) is only honored by the device in MANUAL mode, so
set_percentage switches the device to manual before applying the speed.
Device rotation and blade oscillation are exposed as separate primitives
(switch/select), not on this entity.
"""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from .const import (
    DOMAIN,
    MF10_MODE_MANUAL,
    MF10_MODE_NAME_TO_VALUE,
    MF10_MODE_OPTIONS,
    MF10_POWER_OFF,
    MF10_POWER_ON,
    MF10_PROPERTY_MAP,
    MF10_SPEED_MAX,
    MF10_SPEED_MIN,
    MODEL_MF10,
)
from .coordinator import MF10Coordinator

_SPEED_RANGE = (MF10_SPEED_MIN, MF10_SPEED_MAX)
_PRESET_MODES = list(MF10_MODE_OPTIONS.values())


def _prop(name: str, value: Any) -> dict:
    p = MF10_PROPERTY_MAP[name]
    return {"siid": p["siid"], "piid": p["piid"], "value": value}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MF10Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MF10FanEntity(coordinator, entry.data.get("mac"))])


class MF10FanEntity(CoordinatorEntity[MF10Coordinator], FanEntity):
    """Primary fan entity: power, fan speed, preset modes."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_speed_count = MF10_SPEED_MAX
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_preset_modes = _PRESET_MODES

    def __init__(self, coordinator: MF10Coordinator, mac: str | None) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.did}_fan"
        self._mac = mac
        # Optimistic power state: the action returns code:0 but the device takes
        # ~1-2s to reflect it. Held until a poll confirms the target value, so a
        # premature refresh doesn't snap the UI back.
        self._optimistic_power: int | None = None

    @callback
    def _handle_coordinator_update(self) -> None:
        if (
            self._optimistic_power is not None
            and self.coordinator.data.get("power") == self._optimistic_power
        ):
            self._optimistic_power = None
        super()._handle_coordinator_update()

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
        if self._optimistic_power is not None:
            return self._optimistic_power == MF10_POWER_ON
        power = self.coordinator.data.get("power")
        if power is None:
            return None
        return power == MF10_POWER_ON

    @property
    def percentage(self) -> int | None:
        if not self.is_on:
            return 0
        speed = self.coordinator.data.get("fan_speed")
        if speed is None:
            return None
        return ranged_value_to_percentage(_SPEED_RANGE, speed)

    @property
    def preset_mode(self) -> str | None:
        mode_val = self.coordinator.data.get("mode")
        if mode_val is None:
            return None
        return MF10_MODE_OPTIONS.get(mode_val)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        await self.coordinator.async_set_power(True)
        self._optimistic_power = MF10_POWER_ON

        props: list[dict] = []
        if preset_mode is not None:
            mode_val = MF10_MODE_NAME_TO_VALUE.get(preset_mode)
            if mode_val is None:
                raise HomeAssistantError(f"Unknown preset mode: {preset_mode}")
            props.append(_prop("mode", mode_val))
        if percentage is not None and percentage > 0:
            # Speed is only honored in manual mode.
            speed = math.ceil(percentage_to_ranged_value(_SPEED_RANGE, percentage))
            props.append(_prop("mode", MF10_MODE_MANUAL))
            props.append(_prop("fan_speed", speed))
        if props:
            await self.coordinator.async_set_properties(props)

        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_power(False)
        self._optimistic_power = MF10_POWER_OFF
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            await self.async_turn_off()
            return
        # Speed only takes effect in manual mode; switch mode then set speed.
        speed = math.ceil(percentage_to_ranged_value(_SPEED_RANGE, percentage))
        await self.coordinator.async_set_properties(
            [_prop("mode", MF10_MODE_MANUAL), _prop("fan_speed", speed)]
        )
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        mode_val = MF10_MODE_NAME_TO_VALUE.get(preset_mode)
        if mode_val is None:
            raise HomeAssistantError(f"Unknown preset mode: {preset_mode}")
        await self.coordinator.async_set_properties([_prop("mode", mode_val)])
        await self.coordinator.async_request_refresh()
