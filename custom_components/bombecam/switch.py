"""Switch platform for the BombeCam integration."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import BombeCamError
from .const import (
    ATTR_MOTION,
    ATTR_SOUND,
    ATTR_SPOTLIGHT,
    ATTR_STATUS_LIGHT,
    OPTIMISTIC_GRACE,
)
from .coordinator import BombeCamCoordinator
from .entity import BombeCamEntity

PARALLEL_UPDATES = 0


def _as_bool(value: Any) -> bool | None:
    """Convert a shadow value to a switch state, keeping unknown values unknown."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value == 1:
            return True
        if value == 0:
            return False
        return None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("1", "true", "on"):
            return True
        if normalized in ("0", "false", "off"):
            return False
    return None


@dataclass(frozen=True, kw_only=True)
class BombeCamSwitchDescription(EntityDescription):
    """One switch exposed for a camera."""

    attribute: str
    action: str


SWITCHES: tuple[BombeCamSwitchDescription, ...] = (
    BombeCamSwitchDescription(
        key="status_light",
        name="Status light",
        attribute=ATTR_STATUS_LIGHT,
        action="led",
        icon="mdi:led-on",
    ),
    BombeCamSwitchDescription(
        key="motion_detection",
        name="Motion detection",
        attribute=ATTR_MOTION,
        action="motion",
        icon="mdi:motion-sensor",
    ),
    BombeCamSwitchDescription(
        key="sound_detection",
        name="Sound detection",
        attribute=ATTR_SOUND,
        action="sound",
        icon="mdi:ear-hearing",
    ),
    BombeCamSwitchDescription(
        key="spotlight",
        name="Spotlight",
        attribute=ATTR_SPOTLIGHT,
        action="light",
        icon="mdi:light-flood-down",
    ),
)


class BombeCamSwitch(BombeCamEntity, SwitchEntity):
    """A boolean control backed by one shadow attribute."""

    def __init__(
        self,
        coordinator: BombeCamCoordinator,
        camera_uuid: str,
        description: BombeCamSwitchDescription,
    ) -> None:
        """Create the switch for one camera and one control action."""
        super().__init__(coordinator, camera_uuid)
        self.entity_description = description
        self._attr_name = description.name
        self._attr_unique_id = f"{camera_uuid}_{description.key}"
        self._attr_icon = description.icon
        self._optimistic: bool | None = None
        self._optimistic_at: float | None = None

    @property
    def is_on(self) -> bool | None:
        """Return the optimistic state, or the last value read from the camera."""
        if self._optimistic is not None:
            return self._optimistic
        camera = self.camera
        if camera is None:
            return None
        return _as_bool(camera.value(self.entity_description.attribute))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the control on."""
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the control off."""
        await self._async_set_state(False)

    async def _async_set_state(self, state: bool) -> None:
        """Send one control action, keeping the state optimistic until refreshed."""
        previous = self.is_on
        self._optimistic = state
        self._optimistic_at = monotonic()
        self.async_write_ha_state()
        try:
            await self.coordinator.client.async_control(
                self._camera_uuid,
                self.entity_description.action,
                value=state,
            )
        except BombeCamError as err:
            self._optimistic = previous
            self._optimistic_at = None
            self.async_write_ha_state()
            raise HomeAssistantError(
                f"Cannot set {self.entity_description.name} for "
                f"{self._camera_uuid}: {err}"
            ) from err
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Drop the optimistic state once the camera confirms it or time runs out.

        The shadow can still hold the previous value right after a command
        (the camera answers before it applied the change), so a single stale
        poll must not flip the switch back.
        """
        if self._optimistic is not None:
            camera = self.camera
            reported = (
                _as_bool(camera.value(self.entity_description.attribute))
                if camera is not None
                else None
            )
            expired = (
                self._optimistic_at is None
                or monotonic() - self._optimistic_at >= OPTIMISTIC_GRACE
            )
            if reported is self._optimistic or expired:
                self._optimistic = None
                self._optimistic_at = None
        super()._handle_coordinator_update()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[BombeCamCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switches of every camera reported by the gateway."""
    coordinator: BombeCamCoordinator = entry.runtime_data
    cameras = coordinator.data.cameras if coordinator.data is not None else {}
    async_add_entities(
        BombeCamSwitch(coordinator, camera_uuid, description)
        for camera_uuid in cameras
        for description in SWITCHES
    )
