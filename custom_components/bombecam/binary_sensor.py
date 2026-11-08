"""Binary sensor platform for the BombeCam integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import BombeCamCoordinator
from .entity import BombeCamEntity

PARALLEL_UPDATES = 0


class BombeCamStreamSensor(BombeCamEntity, BinarySensorEntity):
    """Whether the camera is currently streaming, as reported by the gateway."""

    _attr_name = "Stream online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self, coordinator: BombeCamCoordinator, camera_uuid: str
    ) -> None:
        """Create the stream sensor for one camera."""
        super().__init__(coordinator, camera_uuid)
        self._attr_unique_id = f"{camera_uuid}_stream"

    @property
    def is_on(self) -> bool:
        """Return the streaming flag from the gateway payload."""
        camera = self.camera
        if camera is None:
            return False
        return camera.info.streaming


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[BombeCamCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the stream sensor of every camera."""
    coordinator: BombeCamCoordinator = entry.runtime_data
    cameras = coordinator.data.cameras if coordinator.data is not None else {}
    async_add_entities(
        BombeCamStreamSensor(coordinator, camera_uuid) for camera_uuid in cameras
    )
