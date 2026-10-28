from collections.abc import Awaitable, Callable, Generator

import pytest
import respx
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.goma.const import DOMAIN
from custom_components.goma.token_storage import HomeAssistantTokenStorage
from goma.models import Session
from tests.fake_goma import USER_ID, FakeGoma

EMAIL = "someone@example.com"

type SetupIntegration = Callable[[], Awaitable[MockConfigEntry]]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    return None


@pytest.fixture(autouse=True)
def goma_backend(goma: FakeGoma) -> Generator[FakeGoma]:
    """Route every request HA's httpx clients send to the fake goma.

    The integration builds its httpx client as in production, so the real goma library
    runs in these tests; only the transport is replaced.
    """
    with respx.mock(assert_all_called=False) as router:
        router.route().mock(side_effect=goma.handle)
        yield goma


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title=EMAIL, unique_id=USER_ID, data={CONF_EMAIL: EMAIL})
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def setup_integration(
    hass: HomeAssistant, config_entry: MockConfigEntry, goma: FakeGoma
) -> SetupIntegration:
    async def setup() -> MockConfigEntry:
        session = Session.from_auth(goma._issue_session())
        await HomeAssistantTokenStorage(hass, USER_ID).save(session.to_stored())
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        return config_entry

    return setup
