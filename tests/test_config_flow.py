"""Config flow tests for the BombeCam integration."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.bombecam.api import (
    BombeCamAuthError,
    BombeCamConnectionError,
)
from custom_components.bombecam.const import (
    CONF_CODE,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_URL,
    CONF_USERNAME,
    DOMAIN,
)

USER_INPUT = {
    CONF_URL: "192.0.2.10:8654",
    CONF_USERNAME: "admin",
    CONF_PASSWORD: "hunter2hunter2",
}
NORMALIZED_URL = "http://192.0.2.10:8654"


async def test_user_flow_creates_entry(hass, mock_client):
    """A reachable gateway with valid credentials creates one entry."""
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
    assert result["title"] == "BombeCam (192.0.2.10:8654)"
    assert result["data"] == {
        CONF_URL: NORMALIZED_URL,
        CONF_TOKEN: "test-token",
    }
    assert result["result"].unique_id == NORMALIZED_URL
    mock_client["async_generate_token"].assert_awaited_once()
    mock_client["async_validate"].assert_awaited_once()


async def test_user_flow_sends_two_step_code(hass, mock_client):
    """The optional two-step code is forwarded to the token endpoint."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_INPUT, CONF_CODE: "123456"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    mock_client["async_generate_token"].assert_awaited_once()
    assert (
        mock_client["async_generate_token"].call_args.args[4] == "123456"
    )


async def test_user_flow_rejects_bad_credentials(hass, mock_client):
    """A 401/403 from the gateway keeps the form and reports invalid_auth."""
    mock_client["async_generate_token"].side_effect = BombeCamAuthError(
        "credentials rejected"
    )

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
    mock_client["async_generate_token"].side_effect = BombeCamConnectionError(
        "timeout"
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_trims_address(hass, mock_client):
    """Surrounding spaces and a missing scheme are normalized."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_URL: " 192.0.2.10:8654 ",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "hunter2hunter2",
        },
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