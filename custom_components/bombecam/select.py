"""Select platform for the BombeCam integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import BombeCamError
from .const import (
    ATTR_NIGHT_VISION,
    NIGHT_VISION_AUTO,
    NIGHT_VISION_OFF,
)
from .coordinator import BombeCamCoordinator
from .entity import BombeCamEntity

PARALLEL_UPDATES = 0

NIGHT_VISION_OPTIONS: list[str] = [NIGHT_VISION_AUTO, NIGHT_VISION_OFF]


def _as_int(value: Any) -> int | None:
    """Convert a shadow value to an integer, keeping unknown values unknown."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


class BombeCamNightVisionSelect(BombeCamEntity, SelectEntity):
    """Night vision mode of one camera."""

    _attr_name = "Night vision"
    _attr_icon = "mdi:weather-night"
    _attr_options = NIGHT_VISION_OPTIONS

    def __init__(
        self, coordinator: BombeCamCoordinator, camera_uuid: str
    ) -> None:
        """Create the night vision select for one camera."""
        super().__init__(coordinator, camera_uuid)
        self._attr_unique_id = f"{camera_uuid}_night_vision"
        self._optimistic: str | None = None
        self._last_reported: str | None = self._reported_option()

    def _reported_option(self) -> str | None:
        """Return the mode read back from the camera, or None when unknown."""
        camera = self.camera
        if camera is None:
            return None
        mode = _as_int(camera.value(ATTR_NIGHT_VISION))
        if mode == 0:
            return NIGHT_VISION_OFF
        if mode in (1, 2):
            return NIGHT_VISION_AUTO
        return None

    @property
    def current_option(self) -> str | None:
        """Return the optimistic mode, or the last value read from the camera."""
        if self._optimistic is not None:
            return self._optimistic
        reported = self._reported_option()
        return reported if reported is not None else self._last_reported

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the raw readback to make a wrong state diagnosable."""
        return {
            "readback": self._reported_option(),
            "optimistic": self._optimistic is not None,
        }

    async def async_select_option(self, option: str) -> None:
        """Select a night vision mode, keeping it until the camera confirms."""
        if option not in NIGHT_VISION_OPTIONS:
            raise HomeAssistantError(
                f"Unsupported night vision mode for {self._camera_uuid}: {option}"
            )
        self._optimistic = option
        self.async_write_ha_state()
        try:
            await self.coordinator.client.async_control(
                self._camera_uuid, "ir", mode=option
            )
        except BombeCamError as err:
            self._optimistic = None
            self.async_write_ha_state()
            raise HomeAssistantError(
                f"Cannot set night vision for {self._camera_uuid}: {err}"
            ) from err
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Reconcile the optimistic mode with the shadow readback."""
        reported = self._reported_option()
        if reported is not None:
            if self._optimistic is not None:
                if reported == self._optimistic:
                    self._optimistic = None
                elif (
                    self._last_reported is not None
                    and reported != self._last_reported
                ):
                    self._optimistic = None
            self._last_reported = reported
        super()._handle_coordinator_update()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[BombeCamCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the night vision select of every camera."""
    coordinator: BombeCamCoordinator = entry.runtime_data
    cameras = coordinator.data.cameras if coordinator.data is not None else {}
    async_add_entities(
        BombeCamNightVisionSelect(coordinator, camera_uuid)
        for camera_uuid in cameras
    )
