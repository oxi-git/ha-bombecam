"""Button platform for the BombeCam integration."""

from __future__ import annotations

from typing import Final

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BombeCamConfigEntry
from .api import BombeCamError
from .const import (
    CONF_PTZ_DURATION,
    DEFAULT_PTZ_DURATION,
    PTZ_DOWN,
    PTZ_LEFT,
    PTZ_RIGHT,
    PTZ_STOP,
    PTZ_UP,
)
from .coordinator import BombeCamCoordinator
from .entity import BombeCamEntity

PARALLEL_UPDATES: Final = 0

# direction, name, icon; the unique_id is f"{uuid}_ptz_{direction}".
PTZ_BUTTONS: Final = (
    (PTZ_LEFT, "Pan left", "mdi:arrow-left-bold"),
    (PTZ_RIGHT, "Pan right", "mdi:arrow-right-bold"),
    (PTZ_UP, "Tilt up", "mdi:arrow-up-bold"),
    (PTZ_DOWN, "Tilt down", "mdi:arrow-down-bold"),
    (PTZ_STOP, "Stop", "mdi:stop"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BombeCamConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one PTZ button per camera."""
    coordinator: BombeCamCoordinator = entry.runtime_data
    async_add_entities(
        [
            BombeCamPtzButton(coordinator, camera_uuid, direction, name, icon)
            for camera_uuid in coordinator.data.cameras
            for direction, name, icon in PTZ_BUTTONS
        ]
    )


class BombeCamPtzButton(BombeCamEntity, ButtonEntity):
    """One directional PTZ button for one camera."""

    def __init__(
        self,
        coordinator: BombeCamCoordinator,
        camera_uuid: str,
        direction: str,
        name: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, camera_uuid)
        self._direction = direction
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{camera_uuid}_ptz_{direction}"

    async def async_press(self) -> None:
        """Pulse the PTZ motors, or stop them."""
        if self._direction == PTZ_STOP:
            duration = 0
        else:
            duration = self.coordinator.config_entry.options.get(
                CONF_PTZ_DURATION, DEFAULT_PTZ_DURATION
            )
        try:
            await self.coordinator.client.async_ptz(
                self._camera_uuid, self._direction, duration
            )
        except BombeCamError as err:
            raise HomeAssistantError(
                f"PTZ {self._direction} failed for camera {self._camera_uuid}: {err}"
            ) from err


__all__ = ["PARALLEL_UPDATES", "async_setup_entry"]
