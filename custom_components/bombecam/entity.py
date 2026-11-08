"""Shared entity for BombeCam cameras."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import CameraRuntime
from .const import DOMAIN, MANUFACTURER
from .coordinator import BombeCamCoordinator


class BombeCamEntity(CoordinatorEntity[BombeCamCoordinator]):
    """One entity attached to one camera device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: BombeCamCoordinator, camera_uuid: str) -> None:
        super().__init__(coordinator)
        self._camera_uuid = camera_uuid

    @property
    def camera(self) -> CameraRuntime | None:
        """The camera and its shadow state, or None if it disappeared."""
        return self.coordinator.runtime(self._camera_uuid)

    @property
    def available(self) -> bool:
        """Available only while the camera is still reported by the gateway."""
        return super().available and self.camera is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Group every entity of this camera under one device."""
        camera = self.camera
        name = camera.info.name if camera else self._camera_uuid
        model = camera.info.model if camera and camera.info.model else "Camera"
        return DeviceInfo(
            identifiers={(DOMAIN, self._camera_uuid)},
            manufacturer=MANUFACTURER,
            model=model,
            name=name,
            configuration_url=f"{self.coordinator.client.base_url}/",
        )
