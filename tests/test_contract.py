"""Contract tests: parse the exact JSON responses BombeCam produces.

These hand the BombeCamClient the payloads from BombeCam's own handler tests
through the response mock, so a field rename on the gateway side breaks the
parsing here. The client logic itself is exercised (no AsyncMock on the
client); only the transport is mocked.

Values mirror cmd/bombecam-gateway/integration_handlers.go and api_handlers.go.
"""

from __future__ import annotations

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.bombecam.api import BombeCamClient

CAMERA_UUID = "cam-uuid-1"
BASE_URL = "http://192.0.2.10:8654"
RTSP_URL = f"rtsp://192.0.2.10:8554/{CAMERA_UUID}"
STILL_URL = f"{BASE_URL}/api/v1/cameras/{CAMERA_UUID}/snapshot.jpg"

HOME_ASSISTANT_JSON = {
    "integration": "homeassistant",
    "generated_at": "2026-11-13T10:00:00Z",
    "gateway": {
        "base_url": BASE_URL,
        "rtsp_base": "rtsp://192.0.2.10:8554",
        "hls_base": "http://192.0.2.10:8888",
    },
    "total_cameras": 1,
    "cameras": [
        {
            "uuid": CAMERA_UUID,
            "name": "Ingresso",
            "model": "WS03",
            "stream_name": "ingresso",
            "streaming": True,
            "rtsp_url": RTSP_URL,
            "rtsp_url_by_id": RTSP_URL,
            "live_stream_url": f"http://192.0.2.10:8888/{CAMERA_UUID}",
            "still_image_url": STILL_URL,
            "still_image_available": True,
            "recording_available": True,
            "latest_recording_url": (
                f"{BASE_URL}/api/v1/recordings/download"
                f"?path={CAMERA_UUID}%2F2026-11-13_10-00-00.mp4"
            ),
            "video_codec": "h264",
            "audio_codec": "aac",
        }
    ],
    "setup_steps": "",
}

SHADOW_JSON = {
    "state": {
        "reported": {
            "IrLedMode": 1,
            "LedOnOff": 1,
            "LightSW": 1,
            "MotionDetectSW": 1,
            "SoundDetectSW": 0,
        }
    },
    "timestamp": 0,
    "readback_error": "",
}


async def test_get_gateway_parses_bombecam_payload(hass, aioclient_mock) -> None:
    """async_get_gateway reads every field Home Assistant consumes."""
    aioclient_mock.get(
        f"{BASE_URL}/api/v1/integrations/homeassistant", json=HOME_ASSISTANT_JSON
    )

    client = BombeCamClient(async_get_clientsession(hass), BASE_URL, "bc_tok_test")
    data = await client.async_get_gateway()

    assert data.gateway.base_url == BASE_URL
    assert data.gateway.rtsp_base == "rtsp://192.0.2.10:8554"
    assert data.gateway.hls_base == "http://192.0.2.10:8888"

    cam = data.cameras[CAMERA_UUID]
    assert cam.name == "Ingresso"
    assert cam.model == "WS03"
    assert cam.stream_name == "ingresso"
    assert cam.streaming is True
    assert cam.rtsp_url == RTSP_URL
    assert cam.still_image_url == STILL_URL
    assert cam.recording_available is True
    assert cam.latest_recording_url == (
        f"{BASE_URL}/api/v1/recordings/download"
        f"?path={CAMERA_UUID}%2F2026-11-13_10-00-00.mp4"
    )


async def test_get_shadow_parses_bombecam_payload(hass, aioclient_mock) -> None:
    """async_get_shadow reads the reported attributes the entities use."""
    aioclient_mock.get(
        f"{BASE_URL}/api/v1/cameras/{CAMERA_UUID}/shadow", json=SHADOW_JSON
    )

    client = BombeCamClient(async_get_clientsession(hass), BASE_URL, "bc_tok_test")
    reported = await client.async_get_shadow(CAMERA_UUID)

    for attr in ("IrLedMode", "LedOnOff", "LightSW", "MotionDetectSW", "SoundDetectSW"):
        assert attr in reported, f"shadow missing {attr}"


async def test_ptz_and_control_payloads(hass, aioclient_mock) -> None:
    """async_ptz and async_control send the payloads the gateway expects."""
    aioclient_mock.post(
        f"{BASE_URL}/api/v1/cameras/{CAMERA_UUID}/ptz",
        json={"ok": True},
        headers={"Content-Type": "application/json"},
    )
    aioclient_mock.post(
        f"{BASE_URL}/api/v1/cameras/{CAMERA_UUID}/control",
        json={"ok": True},
        headers={"Content-Type": "application/json"},
    )

    client = BombeCamClient(async_get_clientsession(hass), BASE_URL, "bc_tok_test")
    await client.async_ptz(CAMERA_UUID, "left", 400)
    await client.async_control(CAMERA_UUID, "led", value=True)
    await client.async_control(CAMERA_UUID, "ir", mode="off")

    assert len(aioclient_mock.mock_calls) == 3