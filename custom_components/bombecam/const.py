"""Constants for the BombeCam integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "bombecam"

CONF_URL: Final = "url"
CONF_TOKEN: Final = "token"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_PTZ_DURATION: Final = "ptz_duration"

DEFAULT_SCAN_INTERVAL: Final = 30
DEFAULT_PTZ_DURATION: Final = 400
MIN_SCAN_INTERVAL: Final = 10
MAX_SCAN_INTERVAL: Final = 600

REQUEST_TIMEOUT: Final = 10

# How long an optimistic switch/select state may outlive the last command while
# waiting for the camera to confirm it through the shadow. A stale readback
# (the camera answers before it applied the change) must not flip the UI back.
OPTIMISTIC_GRACE: Final = 45

MANUFACTURER: Final = "BombeCam"

PLATFORMS: Final = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CAMERA,
    Platform.SELECT,
    Platform.SWITCH,
]

# Direction names accepted by POST /api/v1/cameras/{uuid}/ptz.
PTZ_LEFT: Final = "left"
PTZ_RIGHT: Final = "right"
PTZ_UP: Final = "up"
PTZ_DOWN: Final = "down"
PTZ_STOP: Final = "stop"

PTZ_DIRECTIONS: Final = {PTZ_LEFT, PTZ_RIGHT, PTZ_UP, PTZ_DOWN, PTZ_STOP}

# Shadow attributes read back from the camera (see GET /api/v1/cameras/{uuid}/shadow).
ATTR_NIGHT_VISION: Final = "IrLedMode"
ATTR_STATUS_LIGHT: Final = "LedOnOff"
ATTR_SPOTLIGHT: Final = "LightSW"
ATTR_MOTION: Final = "MotionDetectSW"
ATTR_SOUND: Final = "SoundDetectSW"

NIGHT_VISION_AUTO: Final = "auto"
NIGHT_VISION_OFF: Final = "off"

SCAN_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
