"""Camera platform for the BombeCam integration."""

from __future__ import annotations

import logging
from typing import Final

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BombeCamConfigEntry
from .coordinator import BombeCamCoordinator
from .entity import BombeCamEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES: Final = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BombeCamConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the camera entity for each camera reported by the gateway."""
    coordinator: BombeCamCoordinator = entry.runtime_data
    async_add_entities(
        [
            BombeCamCamera(coordinator, camera_uuid)
            for camera_uuid in coordinator.data.cameras
        ]
    )


class BombeCamCamera(BombeCamEntity, Camera):
    """The camera entity, with the gateway stream and still image."""

    _attr_supported_features = CameraEntityFeature.STREAM
    _attr_name = None

    def __init__(self, coordinator: BombeCamCoordinator, camera_uuid: str) -> None:
        super().__init__(coordinator, camera_uuid)
        # Camera.__init__ is not reached through the MRO: call it explicitly.
        Camera.__init__(self)
        self._attr_unique_id = f"{camera_uuid}_camera"

    async def stream_source(self) -> str | None:
        """Return the RTSP stream URL reported by the gateway."""
        camera = self.camera
        if camera is None:
            return None
        return camera.info.rtsp_url or None

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Download a still image from the gateway, best effort."""
        camera = self.camera
        if camera is None or not camera.info.still_image_url:
            return None
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(camera.info.still_image_url) as response:
                response.raise_for_status()
                return await response.read()
        except Exception:  # noqa: BLE001 - never raise from the image callback
            _LOGGER.debug(
                "Cannot fetch a still image for camera %s",
                self._camera_uuid,
                exc_info=True,
            )
            return None


__all__ = ["PARALLEL_UPDATES", "async_setup_entry"]
