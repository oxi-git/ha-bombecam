"""Config flow tests for the BombeCam integration."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.bombecam.api import (
    BombeCamAuthError,
    BombeCamConnectionError,
)
from custom_components.bombecam.const import CONF_TOKEN, CONF_URL, DOMAIN

USER_INPUT = {CONF_URL: "192.168.1.12:8654", CONF_TOKEN: "test-token"}
NORMALIZED_URL = "http://192.168.1.12:8654"


async def test_user_flow_creates_entry(hass, mock_client):
    """A reachable gateway with a valid token creates one entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "BombeCam (192.168.1.12:8654)"
    assert result["data"] == {
        CONF_URL: NORMALIZED_URL,
        CONF_TOKEN: "test-token",
    }
    assert result["result"].unique_id == NORMALIZED_URL
    mock_client["async_validate"].assert_awaited_once()


async def test_user_flow_rejects_bad_token(hass, mock_client):
    """A 401/403 from the gateway keeps the form and reports invalid_auth."""
    mock_client["async_validate"].side_effect = BombeCamAuthError("token rejected")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_reports_unreachable_host(hass, mock_client):
    """A network failure keeps the form and reports cannot_connect."""
    mock_client["async_validate"].side_effect = BombeCamConnectionError("timeout")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_strips_bearer_prefix(hass, mock_client):
    """A pasted 'Bearer ' prefix and surrounding spaces are removed."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_URL: " 192.168.1.12:8654 ", CONF_TOKEN: " Bearer test-token "},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_URL: NORMALIZED_URL,
        CONF_TOKEN: "test-token",
    }


async def test_user_flow_aborts_for_configured_host(hass, mock_client, entry_factory):
    """The same normalized address cannot be added twice."""
    entry_factory()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
