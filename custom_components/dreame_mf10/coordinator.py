"""DataUpdateCoordinator for the Dreame MF10 integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_POLLING_INTERVAL, DOMAIN, MF10_PROPERTY_MAP
from .dreame_cloud import DreameApiError, DreameAuthError, DreameCloud, DreameConnectionError

_LOGGER = logging.getLogger(__name__)

# Property list is built from the validated MF10_PROPERTY_MAP. All entries here
# are confirmed via before/after scan (docs/property_map.md) — do NOT add
# unvalidated (siid, piid) pairs, as an unknown property makes Dreame reject
# the entire envelope with code=80001.
_POLL_PROPERTIES = [
    {"siid": v["siid"], "piid": v["piid"]} for v in MF10_PROPERTY_MAP.values()
]
_SIID_PIID_TO_NAME = {
    (v["siid"], v["piid"]): k for k, v in MF10_PROPERTY_MAP.items()
}


class MF10Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the Dreame MF10 every DEFAULT_POLLING_INTERVAL seconds."""

    def __init__(
        self,
        hass: HomeAssistant,
        cloud: DreameCloud,
        did: str,
        host: str | None,
    ) -> None:
        self._cloud = cloud
        self._did = did
        self._host = host
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{did}",
            update_interval=timedelta(seconds=DEFAULT_POLLING_INTERVAL),
        )

    @property
    def did(self) -> str:
        return self._did

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            results = await self._cloud.async_get_properties(
                self._did, _POLL_PROPERTIES, host=self._host
            )
        except DreameAuthError as err:
            # TODO(M4-hardening): async_step_reauth not yet implemented in config_flow.
            # ConfigEntryAuthFailed will mark the entry as REAUTH_REQUIRED in HA UI.
            raise ConfigEntryAuthFailed(err) from err
        except (DreameConnectionError, DreameApiError) as err:
            raise UpdateFailed(err) from err

        data: dict[str, Any] = {}
        for item in results:
            key = (item.get("siid"), item.get("piid"))
            name = _SIID_PIID_TO_NAME.get(key)
            if name is None:
                continue
            if item.get("code") != 0:
                _LOGGER.debug("Property %s returned code=%s, skipping", name, item.get("code"))
                continue
            data[name] = item.get("value")

        return data
