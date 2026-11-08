"""Shared fixtures for the BombeCam tests."""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bombecam.api import (
    CameraInfo,
    GatewayData,
    GatewayInfo,
)
from custom_components.bombecam.const import CONF_TOKEN, CONF_URL, DOMAIN

pytest_plugins = "pytest_homeassistant_custom_component"

BASE_URL = "http://192.168.1.12:8654"
TOKEN = "test-token"
RTSP_URL = "rtsp://192.168.1.12:8554/ingresso"
STILL_IMAGE_URL = f"{BASE_URL}/api/v1/cameras/cam1/snapshot.jpg"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Iterator[None]:
    """Load custom integrations in every test."""
    yield


@pytest.fixture
def gateway_data() -> GatewayData:
    """Return one gateway with a single camera."""
    return GatewayData(
        gateway=GatewayInfo(base_url=BASE_URL),
        cameras={
            "cam1": CameraInfo(
                uuid="cam1",
                name="Ingresso",
                model="WS03",
                streaming=True,
                rtsp_url=RTSP_URL,
                still_image_url=STILL_IMAGE_URL,
                stream_name="ingresso",
            )
        },
    )


@pytest.fixture
def mock_client(gateway_data: GatewayData) -> Iterator[dict[str, AsyncMock]]:
    """Replace every gateway call with an AsyncMock.

    The mocks are class attributes, so they receive the arguments exactly as
    the integration passes them (no bound ``self``).
    """
    with patch.multiple(
        "custom_components.bombecam.api.BombeCamClient",
        async_validate=AsyncMock(return_value=gateway_data),
        async_get_gateway=AsyncMock(return_value=gateway_data),
        async_get_shadow=AsyncMock(return_value={}),
        async_ptz=AsyncMock(return_value={}),
        async_control=AsyncMock(return_value={}),
    ) as mocks:
        yield mocks


@pytest.fixture
def entry_factory(hass):
    """Return a factory that creates a configured BombeCam entry."""

    def _create(**kwargs) -> MockConfigEntry:
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="BombeCam (192.168.1.12:8654)",
            data={CONF_URL: BASE_URL, CONF_TOKEN: TOKEN},
            unique_id=BASE_URL,
            **kwargs,
        )
        entry.add_to_hass(hass)
        return entry

    return _create


@pytest.fixture
def bombecam_entry(entry_factory) -> MockConfigEntry:
    """Return a configured BombeCam entry added to the test hass."""
    return entry_factory()
