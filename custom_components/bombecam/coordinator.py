"""Coordinator that polls the BombeCam gateway."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    BombeCamAuthError,
    BombeCamClient,
    BombeCamConnectionError,
    BombeCamError,
    CameraRuntime,
    GatewayData,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class BombeCamCoordinator(DataUpdateCoordinator[GatewayData]):
    """Poll the gateway and keep each camera's shadow state next to it."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: BombeCamClient,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.config_entry = entry
        self.client = client
        self.shadow: dict[str, dict[str, Any]] = {}

    async def _async_update_data(self) -> GatewayData:
        try:
            data = await self.client.async_get_gateway()
        except BombeCamAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except BombeCamConnectionError as err:
            raise UpdateFailed(f"cannot reach BombeCam: {err}") from err
        except BombeCamError as err:
            raise UpdateFailed(str(err)) from err

        shadow: dict[str, dict[str, Any]] = {}
        for camera_uuid in data.cameras:
            try:
                reported = await self.client.async_get_shadow(camera_uuid)
            except BombeCamAuthError as err:
                raise ConfigEntryAuthFailed(str(err)) from err
            except BombeCamError:
                # A camera without a live control channel still has a stream:
                # keep it, just without readback.
                reported = {}
            shadow[camera_uuid] = reported
        self.shadow = shadow
        return data

    def runtime(self, camera_uuid: str) -> CameraRuntime | None:
        """Return the camera together with its last shadow state."""
        if self.data is None:
            return None
        info = self.data.cameras.get(camera_uuid)
        if info is None:
            return None
        return CameraRuntime(info=info, reported=self.shadow.get(camera_uuid, {}))
