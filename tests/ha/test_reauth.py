from datetime import timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult, FlowResultType
from homeassistant.helpers.translation import async_get_translations
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.goma.const import DOMAIN
from custom_components.goma.token_storage import HomeAssistantTokenStorage
from tests.fake_goma import USER_ID, FakeGoma
from tests.ha.conftest import EMAIL, SetupIntegration


def reauth_flows(hass: HomeAssistant, entry: MockConfigEntry) -> list:
    return [
        flow
        for flow in hass.config_entries.flow.async_progress_by_handler(DOMAIN)
        if flow["context"].get("source") == SOURCE_REAUTH
        and flow["context"].get("entry_id") == entry.entry_id
    ]


async def end_session(hass: HomeAssistant, goma: FakeGoma, freezer: FrozenDateTimeFactory) -> None:
    goma.revoke_access_tokens()
    goma.reject_refresh = True
    freezer.tick(timedelta(hours=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def reauth_with_code(hass: HomeAssistant, entry: MockConfigEntry, code: str) -> FlowResult:
    [flow] = reauth_flows(hass, entry)
    result = await hass.config_entries.flow.async_configure(flow["flow_id"], {})
    assert result["step_id"] == "code"
    return await hass.config_entries.flow.async_configure(flow["flow_id"], {"code": code})


async def test_an_ended_session_asks_to_log_in_again(
    hass: HomeAssistant,
    setup_integration: SetupIntegration,
    goma: FakeGoma,
    freezer: FrozenDateTimeFactory,
) -> None:
    entry = await setup_integration()

    await end_session(hass, goma, freezer)

    assert len(reauth_flows(hass, entry)) == 1


async def test_logging_in_again_brings_the_lists_back(
    hass: HomeAssistant,
    setup_integration: SetupIntegration,
    goma: FakeGoma,
    freezer: FrozenDateTimeFactory,
) -> None:
    entry = await setup_integration()
    await end_session(hass, goma, freezer)
    goma.reject_refresh = False
    sent_before = len(goma.codes_sent_to)

    result = await reauth_with_code(hass, entry, goma.code)
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert goma.codes_sent_to[sent_before:] == [{"email": EMAIL, "create_user": False}]
    assert entry.state is ConfigEntryState.LOADED
    assert reauth_flows(hass, entry) == []
    stored = await HomeAssistantTokenStorage(hass, USER_ID).load()
    assert stored is not None
    assert stored["access_token"] in goma._valid_access


async def test_a_code_for_another_account_is_refused(
    hass: HomeAssistant,
    setup_integration: SetupIntegration,
    goma: FakeGoma,
    freezer: FrozenDateTimeFactory,
) -> None:
    entry = await setup_integration()
    await end_session(hass, goma, freezer)
    goma.user_id = "00000000-0000-0000-0000-00000000beef"

    result = await reauth_with_code(hass, entry, goma.code)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_account"
    assert await HomeAssistantTokenStorage(hass, goma.user_id).load() is None


@pytest.mark.parametrize("language", ["en", "da"])
async def test_texts_are_translated(hass: HomeAssistant, language: str) -> None:
    config = await async_get_translations(hass, language, "config", [DOMAIN])
    exceptions = await async_get_translations(hass, language, "exceptions", [DOMAIN])
    prefix = f"component.{DOMAIN}"

    assert "{email}" in config[f"{prefix}.config.step.code.description"]
    assert "{email}" in config[f"{prefix}.config.step.reauth_confirm.description"]
    for error in ("cannot_connect", "code_not_sent", "invalid_code", "unknown"):
        assert config[f"{prefix}.config.error.{error}"]
    assert config[f"{prefix}.config.abort.wrong_account"]
    assert "{error}" in exceptions[f"{prefix}.exceptions.auth_failed.message"]
