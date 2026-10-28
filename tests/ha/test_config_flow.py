from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult, FlowResultType

from custom_components.goma.const import DOMAIN
from custom_components.goma.token_storage import HomeAssistantTokenStorage
from tests.fake_goma import USER_ID, FakeGoma
from tests.ha.conftest import EMAIL, SetupIntegration


async def submit_email(hass: HomeAssistant, email: str = EMAIL) -> FlowResult:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    return await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_EMAIL: email})


async def test_login_with_the_emailed_code_creates_the_entry(
    hass: HomeAssistant, goma: FakeGoma
) -> None:
    result = await submit_email(hass, f"  {EMAIL} ")

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "code"
    assert goma.codes_sent_to == [{"email": EMAIL, "create_user": False}]

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"code": goma.code})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == EMAIL
    assert result["data"] == {CONF_EMAIL: EMAIL}
    assert result["result"].unique_id == USER_ID
    stored = await HomeAssistantTokenStorage(hass, USER_ID).load()
    assert stored is not None
    assert stored["refresh_token"] == "refresh-1"


async def test_a_wrong_code_can_be_corrected(hass: HomeAssistant, goma: FakeGoma) -> None:
    result = await submit_email(hass)

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"code": "000000"})

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "code"
    assert result["errors"] == {"base": "invalid_code"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"code": goma.code})
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_goma_unreachable_keeps_the_email_form(hass: HomeAssistant, goma: FakeGoma) -> None:
    goma.down = True

    result = await submit_email(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_the_same_account_cannot_be_added_twice(
    hass: HomeAssistant, setup_integration: SetupIntegration, goma: FakeGoma
) -> None:
    await setup_integration()
    result = await submit_email(hass)

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"code": goma.code})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
