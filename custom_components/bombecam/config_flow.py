"""Config and options flow for BombeCam."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_URL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    BombeCamAuthError,
    BombeCamClient,
    BombeCamConnectionError,
    BombeCamError,
    normalize_token,
)
from .const import (
    CONF_PTZ_DURATION,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    DEFAULT_PTZ_DURATION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)


def _title(url: str) -> str:
    """Name the entry after the gateway host."""
    return f"BombeCam ({urlparse(url).netloc or url})"


class BombeCamConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for the gateway address and an API token."""

    VERSION = 1

    async def _async_validate(
        self, url: str, token: str
    ) -> tuple[BombeCamClient | None, str | None]:
        """Check that the address answers and the token is accepted."""
        client = BombeCamClient(async_get_clientsession(self.hass), url, token)
        try:
            await client.async_validate()
        except BombeCamAuthError:
            return None, "invalid_auth"
        except BombeCamConnectionError:
            return None, "cannot_connect"
        except BombeCamError:
            return None, "unknown"
        return client, None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the first step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            token = normalize_token(user_input[CONF_TOKEN])
            client, error = await self._async_validate(user_input[CONF_URL], token)
            if client is not None:
                await self.async_set_unique_id(client.base_url)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=_title(client.base_url),
                    data={
                        CONF_URL: client.base_url,
                        CONF_TOKEN: token,
                    },
                )
            if error is not None:
                errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_URL): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.URL)
                    ),
                    vol.Required(CONF_TOKEN): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Start a re-authentication after a rejected token."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a fresh token and keep the same address."""
        errors: dict[str, str] = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry is None:
            return self.async_abort(reason="reauth_entry_missing")

        if user_input is not None:
            token = normalize_token(user_input[CONF_TOKEN])
            client, error = await self._async_validate(entry.data[CONF_URL], token)
            if client is not None:
                return self.async_update_reload_and_abort(
                    entry,
                    data={**entry.data, CONF_TOKEN: token},
                )
            if error is not None:
                errors["base"] = error

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TOKEN): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
            description_placeholders={"url": entry.data[CONF_URL]},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return BombeCamOptionsFlow()


class BombeCamOptionsFlow(OptionsFlow):
    """Polling interval and PTZ pulse length."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the polling interval and the default pulse."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    ),
                    vol.Optional(
                        CONF_PTZ_DURATION,
                        default=options.get(CONF_PTZ_DURATION, DEFAULT_PTZ_DURATION),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=100,
                            max=2000,
                            step=50,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="ms",
                        )
                    ),
                }
            ),
        )
