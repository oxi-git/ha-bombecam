"""Diagnostics for the BombeCam integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_TOKEN

TO_REDACT = {CONF_TOKEN}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry
) -> dict[str, Any]:
    """Return the gateway state without the API token or stream URLs."""
    coordinator = entry.runtime_data
    data = coordinator.data
    cameras: dict[str, Any] = {}
    if data is not None:
        for uuid, info in data.cameras.items():
            cameras[uuid] = {
                "name": info.name,
                "model": info.model,
                "streaming": info.streaming,
                "has_rtsp_url": bool(info.rtsp_url),
                "has_still_image": bool(info.still_image_url),
                "shadow": coordinator.shadow.get(uuid, {}),
            }
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "gateway": asdict(data.gateway) if data is not None else None,
        "cameras": cameras,
    }
