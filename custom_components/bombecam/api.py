"""Async client for the BombeCam gateway REST API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import PTZ_DIRECTIONS, REQUEST_TIMEOUT


class BombeCamError(Exception):
    """Base class for BombeCam errors."""


class BombeCamAuthError(BombeCamError):
    """The gateway rejected the API token."""


class BombeCamConnectionError(BombeCamError):
    """The gateway could not be reached."""


class BombeCamApiError(BombeCamError):
    """The gateway answered with an error."""


def normalize_url(value: str) -> str:
    """Return a base URL with a scheme and no trailing slash."""
    url = value.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    return url


def normalize_token(value: str) -> str:
    """Return the bare API token, dropping spaces and an accidental Bearer prefix."""
    token = value.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token


@dataclass(slots=True)
class GatewayInfo:
    """Addresses the gateway reports for its own streams."""

    base_url: str
    rtsp_base: str = ""
    hls_base: str = ""


@dataclass(slots=True)
class CameraInfo:
    """One camera as described by /api/v1/integrations/homeassistant."""

    uuid: str
    name: str
    model: str = ""
    streaming: bool = False
    rtsp_url: str = ""
    still_image_url: str | None = None
    stream_name: str = ""
    recording_available: bool = False
    latest_recording_url: str | None = None


@dataclass(slots=True)
class GatewayData:
    """Everything the coordinator needs for one refresh."""

    gateway: GatewayInfo
    cameras: dict[str, CameraInfo] = field(default_factory=dict)


@dataclass(slots=True)
class CameraRuntime:
    """A camera plus the last shadow state read back from it."""

    info: CameraInfo
    reported: dict[str, Any] = field(default_factory=dict)

    def value(self, attribute: str) -> Any:
        """Return a reported shadow value, or None when it is unknown."""
        return self.reported.get(attribute)


class BombeCamClient:
    """Minimal client for the endpoints this integration uses."""

    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        token: str,
        timeout: int = REQUEST_TIMEOUT,
    ) -> None:
        self._session = session
        self.base_url = normalize_url(base_url)
        self._token = normalize_token(token)
        self._timeout = ClientTimeout(total=timeout)

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            async with self._session.request(
                method,
                url,
                json=payload,
                headers=self._headers,
                timeout=self._timeout,
            ) as response:
                body = await response.text()
                if response.status in (401, 403):
                    raise BombeCamAuthError(body[:200] or "token rejected")
                if response.status >= 400:
                    raise BombeCamApiError(f"HTTP {response.status}: {body[:200]}")
                if not body:
                    return {}
                try:
                    data = await response.json(content_type=None)
                except ValueError as err:
                    raise BombeCamApiError(f"invalid JSON from {path}: {err}") from err
        except ClientError as err:
            raise BombeCamConnectionError(str(err)) from err
        except TimeoutError as err:
            raise BombeCamConnectionError("timeout") from err
        if not isinstance(data, dict):
            raise BombeCamApiError(f"unexpected payload from {path}")
        return data

    async def async_validate(self) -> GatewayData:
        """Fetch the integration view, which also proves the token works."""
        return await self.async_get_gateway()

    async def async_get_gateway(self) -> GatewayData:
        """Return the gateway and its cameras."""
        data = await self._request("GET", "/api/v1/integrations/homeassistant")
        gateway_raw = data.get("gateway") or {}
        gateway = GatewayInfo(
            base_url=gateway_raw.get("base_url") or self.base_url,
            rtsp_base=gateway_raw.get("rtsp_base") or "",
            hls_base=gateway_raw.get("hls_base") or "",
        )
        cameras: dict[str, CameraInfo] = {}
        for raw in data.get("cameras") or []:
            uuid = (raw.get("uuid") or "").strip()
            if not uuid:
                continue
            cameras[uuid] = CameraInfo(
                uuid=uuid,
                name=(raw.get("name") or uuid).strip(),
                model=(raw.get("model") or "").strip(),
                streaming=bool(raw.get("streaming")),
                rtsp_url=(raw.get("rtsp_url") or "").strip(),
                still_image_url=(raw.get("still_image_url") or None),
                stream_name=(raw.get("stream_name") or "").strip(),
                recording_available=bool(raw.get("recording_available")),
                latest_recording_url=(raw.get("latest_recording_url") or None),
            )
        return GatewayData(gateway=gateway, cameras=cameras)

    async def async_get_shadow(self, camera_uuid: str) -> dict[str, Any]:
        """Return the camera's reported shadow attributes, best effort."""
        data = await self._request("GET", f"/api/v1/cameras/{camera_uuid}/shadow")
        state = data.get("state") or {}
        reported = state.get("reported") or {}
        return reported if isinstance(reported, dict) else {}

    async def async_ptz(
        self, camera_uuid: str, direction: str, duration_ms: int
    ) -> dict[str, Any]:
        """Pulse the pan/tilt motors."""
        if direction not in PTZ_DIRECTIONS:
            raise ValueError(f"unsupported direction: {direction}")
        return await self._request(
            "POST",
            f"/api/v1/cameras/{camera_uuid}/ptz",
            {"direction": direction, "duration_ms": int(duration_ms)},
        )

    async def async_control(
        self, camera_uuid: str, action: str, **values: Any
    ) -> dict[str, Any]:
        """Send one control action (ir, led, light, motion, sound)."""
        payload: dict[str, Any] = {"action": action}
        payload.update({key: value for key, value in values.items() if value is not None})
        return await self._request(
            "POST", f"/api/v1/cameras/{camera_uuid}/control", payload
        )
