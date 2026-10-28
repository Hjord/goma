from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_EMAIL
from homeassistant.core import callback
from homeassistant.helpers.httpx_client import create_async_httpx_client
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from goma import GomaClient, GomaError, GomaUnreachableError, InvalidCodeError, TokenStorage

from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MINUTES, DOMAIN, LOGGER
from .token_storage import HomeAssistantTokenStorage

CONF_CODE = "code"

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
        )
    }
)
CODE_SCHEMA = vol.Schema(
    {vol.Required(CONF_CODE): TextSelector(TextSelectorConfig(autocomplete="one-time-code"))}
)
OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL_MINUTES): vol.All(
            NumberSelector(
                NumberSelectorConfig(
                    min=5,
                    max=1440,
                    step=5,
                    unit_of_measurement="min",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Coerce(int),
        )
    }
)


class _PendingSession(TokenStorage):
    """Holds the session from the login until the goma user id is known."""

    def __init__(self) -> None:
        self.data: dict[str, Any] | None = None

    async def load(self) -> dict[str, Any] | None:
        return self.data

    async def save(self, data: dict[str, Any]) -> None:
        self.data = data


class GomaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Logs in with the code goma emails: first the email, then the code."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "GomaOptionsFlow":
        return GomaOptionsFlow()

    def __init__(self) -> None:
        self._email = ""
        self._pending = _PendingSession()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._email = user_input[CONF_EMAIL].strip()
            errors = await self._async_send_code()
            if not errors:
                return await self.async_step_code()
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        self._email = entry_data[CONF_EMAIL]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await self._async_send_code()
            if not errors:
                return await self.async_step_code()
        return self.async_show_form(
            step_id="reauth_confirm",
            description_placeholders={"email": self._email},
            errors=errors,
        )

    async def async_step_code(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                user_id = await self._client(self._pending).verify_code(
                    self._email, user_input[CONF_CODE]
                )
            except InvalidCodeError:
                errors["base"] = "invalid_code"
            except GomaUnreachableError:
                errors["base"] = "cannot_connect"
            except GomaError:
                LOGGER.exception("Unexpected answer from goma while logging in")
                errors["base"] = "unknown"
            else:
                return await self._async_finish(user_id)
        return self.async_show_form(
            step_id="code",
            data_schema=CODE_SCHEMA,
            description_placeholders={"email": self._email},
            errors=errors,
        )

    async def _async_finish(self, user_id: str) -> ConfigFlowResult:
        await self.async_set_unique_id(user_id)
        if self.source == SOURCE_REAUTH:
            self._abort_if_unique_id_mismatch(reason="wrong_account")
        else:
            self._abort_if_unique_id_configured()
        assert self._pending.data is not None
        await HomeAssistantTokenStorage(self.hass, user_id).save(self._pending.data)
        if self.source == SOURCE_REAUTH:
            return self.async_update_reload_and_abort(self._get_reauth_entry())
        return self.async_create_entry(title=self._email, data={CONF_EMAIL: self._email})

    async def _async_send_code(self) -> dict[str, str]:
        try:
            await self._client(None).request_code(self._email)
        except GomaUnreachableError:
            return {"base": "cannot_connect"}
        except GomaError:
            LOGGER.warning("goma would not send a login code to %s", self._email)
            return {"base": "code_not_sent"}
        return {}

    def _client(self, storage: TokenStorage | None) -> GomaClient:
        return GomaClient(token_storage=storage, httpx_client=create_async_httpx_client(self.hass))


class GomaOptionsFlow(OptionsFlowWithReload):
    """Sets how often the lists are read. The entry reloads to apply it."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )
