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


class BombeCamRecordingSensor(BombeCamEntity, BinarySensorEntity):
    """Whether the gateway has recorded a segment for this camera.

    The on-board recording is on-demand: a segment exists only while the
    stream was published. The sensor reports ON when at least one segment is
    ready, and exposes the download URL of the newest one as an attribute.
    """

    _attr_name = "Recording"
    _attr_device_class = BinarySensorDeviceClass.PRESENCE

    def __init__(
        self, coordinator: BombeCamCoordinator, camera_uuid: str
    ) -> None:
        """Create the recording sensor for one camera."""
        super().__init__(coordinator, camera_uuid)
        self._attr_unique_id = f"{camera_uuid}_recording"

    @property
    def is_on(self) -> bool | None:
        """Return whether a recording is available for this camera."""
        camera = self.camera
        if camera is None:
            return None
        return camera.info.recording_available

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Expose the newest recording download URL when there is one."""
        camera = self.camera
        if camera is None or not camera.info.latest_recording_url:
            return None
        return {"latest_recording_url": camera.info.latest_recording_url}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[BombeCamCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the stream and recording sensors of every camera."""
    coordinator: BombeCamCoordinator = entry.runtime_data
    cameras = coordinator.data.cameras if coordinator.data is not None else {}
    async_add_entities(
        entity
        for camera_uuid in cameras
        for entity in (
            BombeCamStreamSensor(coordinator, camera_uuid),
            BombeCamRecordingSensor(coordinator, camera_uuid),
        )
    )
