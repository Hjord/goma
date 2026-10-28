from datetime import timedelta
from typing import Any

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from tests.fake_goma import USER_ID, FakeGoma
from tests.ha.conftest import SetupIntegration


def entity_id(hass: HomeAssistant, list_id: int) -> str:
    found = er.async_get(hass).async_get_entity_id("todo", "goma", f"{USER_ID}_{list_id}")
    assert found is not None
    return found


async def items(hass: HomeAssistant, entity: str) -> list[dict[str, Any]]:
    response = await hass.services.async_call(
        "todo", "get_items", {"entity_id": entity}, blocking=True, return_response=True
    )
    return response[entity]["items"]  # type: ignore[index]


async def next_poll(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    freezer.tick(timedelta(hours=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_each_list_is_a_todo_list_named_after_it(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    await setup_integration()

    main = hass.states.get(entity_id(hass, 3))
    weekend = hass.states.get(entity_id(hass, 7))
    assert main is not None
    assert weekend is not None
    assert main.attributes["friendly_name"].endswith("Indkøbsliste")
    assert main.state == "3"
    assert weekend.state == "1"


async def test_items_show_quantity_status_and_product(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    await setup_integration()

    found = await items(hass, entity_id(hass, 3))

    assert [(item["summary"], item["status"]) for item in found] == [
        ("2 x Creme fraiche 38% fedt øko", "needs_action"),
        ("Kartofler", "completed"),
        ("Salt", "needs_action"),
        ("Mælk", "needs_action"),
    ]
    assert found[0]["description"] == "Salling ØKO · Bilka"
    assert "description" not in found[2]


async def test_changes_on_goma_show_up_after_the_next_poll(
    hass: HomeAssistant,
    setup_integration: SetupIntegration,
    goma: FakeGoma,
    freezer: FrozenDateTimeFactory,
) -> None:
    await setup_integration()
    goma.items[0]["is_picked"] = True
    goma.lists[0]["name"] = "Fredag"

    await next_poll(hass, freezer)

    main = hass.states.get(entity_id(hass, 3))
    weekend = hass.states.get(entity_id(hass, 7))
    assert main is not None
    assert weekend is not None
    assert main.state == "2"
    assert weekend.attributes["friendly_name"].endswith("Fredag")


async def test_a_new_list_gets_its_own_entity(
    hass: HomeAssistant,
    setup_integration: SetupIntegration,
    goma: FakeGoma,
    freezer: FrozenDateTimeFactory,
) -> None:
    await setup_integration()
    goma.lists.append(
        {"id": 11, "name": "Fest", "user_id": "u", "group_id": "g-2", "deleted_at": None}
    )

    await next_poll(hass, freezer)

    state = hass.states.get(entity_id(hass, 11))
    assert state is not None
    assert state.state == "0"


async def test_a_deleted_list_becomes_unavailable(
    hass: HomeAssistant,
    setup_integration: SetupIntegration,
    goma: FakeGoma,
    freezer: FrozenDateTimeFactory,
) -> None:
    await setup_integration()
    goma.lists[0]["deleted_at"] = "2026-10-28T12:00:00+00:00"

    await next_poll(hass, freezer)

    state = hass.states.get(entity_id(hass, 7))
    assert state is not None
    assert state.state == STATE_UNAVAILABLE


async def test_goma_down_makes_the_lists_unavailable(
    hass: HomeAssistant,
    setup_integration: SetupIntegration,
    goma: FakeGoma,
    freezer: FrozenDateTimeFactory,
) -> None:
    await setup_integration()
    goma.down = True

    await next_poll(hass, freezer)

    state = hass.states.get(entity_id(hass, 3))
    assert state is not None
    assert state.state == STATE_UNAVAILABLE
