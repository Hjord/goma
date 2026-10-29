from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from tests.fake_goma import FakeGoma
from tests.ha.conftest import SetupIntegration
from tests.ha.test_reauth import reauth_flows
from tests.ha.test_todo import entity_id


async def get_items(hass: HomeAssistant, entity: str) -> list[dict[str, Any]]:
    response = await hass.services.async_call(
        "goma", "get_items", {"entity_id": entity}, blocking=True, return_response=True
    )
    return response[entity]["items"]  # type: ignore[index]


async def test_items_carry_their_bilka_article_number(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    await setup_integration()

    found = await get_items(hass, entity_id(hass, 3))

    assert found[0] == {
        "id": 101,
        "name": "Creme fraiche 38% fedt øko",
        "quantity": 2,
        "picked": False,
        "bilka_article_number": "85164",
        "product_id": "bilka-85164",
        "brand": "Salling ØKO",
        "store": "Bilka",
    }
    assert [(item["name"], item["picked"], item["bilka_article_number"]) for item in found] == [
        ("Creme fraiche 38% fedt øko", False, "85164"),
        ("Kartofler", True, "51138"),
        ("Salt", False, None),
        ("Mælk", False, None),
    ]


async def test_reads_goma_now_not_the_last_poll(
    hass: HomeAssistant, setup_integration: SetupIntegration, goma: FakeGoma
) -> None:
    await setup_integration()
    goma.items[0]["quantity"] = 5

    found = await get_items(hass, entity_id(hass, 3))

    assert found[0]["quantity"] == 5


async def test_an_ended_session_fails_the_action_and_asks_to_log_in_again(
    hass: HomeAssistant, setup_integration: SetupIntegration, goma: FakeGoma
) -> None:
    entry = await setup_integration()
    goma.revoke_access_tokens()
    goma.reject_refresh = True

    with pytest.raises(HomeAssistantError, match="Log in to goma again"):
        await get_items(hass, entity_id(hass, 3))
    await hass.async_block_till_done()

    assert len(reauth_flows(hass, entry)) == 1


async def test_goma_down_fails_the_action(
    hass: HomeAssistant, setup_integration: SetupIntegration, goma: FakeGoma
) -> None:
    await setup_integration()
    goma.down = True

    with pytest.raises(HomeAssistantError, match="Could not read the goma shopping list"):
        await get_items(hass, entity_id(hass, 3))
