from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.goma.const import CONF_UPDATE_INTERVAL
from tests.fake_goma import USER_ID, FakeGoma
from tests.ha.conftest import SetupIntegration
from tests.ha.test_todo import entity_id


def open_items(hass: HomeAssistant) -> str:
    state = hass.states.get(entity_id(hass, 3))
    assert state is not None
    return state.state


async def wait(hass: HomeAssistant, freezer: FrozenDateTimeFactory, minutes: int) -> None:
    freezer.tick(timedelta(minutes=minutes))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_lists_are_read_once_an_hour_by_default(
    hass: HomeAssistant,
    setup_integration: SetupIntegration,
    goma: FakeGoma,
    freezer: FrozenDateTimeFactory,
) -> None:
    await setup_integration()
    goma.items[0]["is_picked"] = True

    await wait(hass, freezer, 59)
    assert open_items(hass) == "3"

    await wait(hass, freezer, 1)
    assert open_items(hass) == "2"


async def test_the_refresh_button_reads_the_lists_now(
    hass: HomeAssistant, setup_integration: SetupIntegration, goma: FakeGoma
) -> None:
    await setup_integration()
    goma.items[0]["is_picked"] = True
    button = er.async_get(hass).async_get_entity_id("button", "goma", f"{USER_ID}_refresh")
    assert button is not None

    await hass.services.async_call("button", "press", {"entity_id": button}, blocking=True)
    await hass.async_block_till_done()

    assert open_items(hass) == "2"


async def test_the_interval_can_be_changed_in_the_options(
    hass: HomeAssistant,
    setup_integration: SetupIntegration,
    goma: FakeGoma,
    freezer: FrozenDateTimeFactory,
) -> None:
    entry = await setup_integration()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_UPDATE_INTERVAL: 15}
    )
    await hass.async_block_till_done()
    assert entry.options == {CONF_UPDATE_INTERVAL: 15}

    goma.items[0]["is_picked"] = True
    await wait(hass, freezer, 15)
    assert open_items(hass) == "2"
