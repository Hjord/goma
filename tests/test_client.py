from decimal import Decimal

import httpx
import pytest

from goma import (
    GomaClient,
    GomaUnreachableError,
    InvalidCodeError,
    NotLoggedInError,
)

from .conftest import MemoryTokenStorage
from .fake_goma import USER_ID, FakeGoma


async def test_request_code_never_creates_an_account(client: GomaClient, goma: FakeGoma) -> None:
    await client.request_code("someone@example.com")

    assert goma.codes_sent_to == [{"email": "someone@example.com", "create_user": False}]


async def test_verify_code_stores_the_session(
    client: GomaClient, goma: FakeGoma, storage: MemoryTokenStorage
) -> None:
    user_id = await client.verify_code("someone@example.com", goma.code)

    assert user_id == USER_ID
    assert storage.data is not None
    assert storage.data["refresh_token"] == "refresh-1"
    assert storage.data["user_id"] == USER_ID


async def test_wrong_code_is_rejected_and_nothing_is_stored(
    client: GomaClient, storage: MemoryTokenStorage
) -> None:
    with pytest.raises(InvalidCodeError):
        await client.verify_code("someone@example.com", "000000")

    assert storage.data is None


async def test_reading_without_a_session_asks_for_login(client: GomaClient) -> None:
    with pytest.raises(NotLoggedInError):
        await client.get_lists()


async def test_lists_exclude_deleted_and_mark_the_primary(logged_in: GomaClient) -> None:
    lists = await logged_in.get_lists()

    assert [(lst.id, lst.name, lst.is_primary) for lst in lists] == [
        (7, "Weekend", False),
        (3, "Indkøbsliste", True),
    ]


async def test_items_skip_picked_and_hidden_and_carry_products(logged_in: GomaClient) -> None:
    items = await logged_in.get_items(3)

    assert [item.id for item in items] == [101, 103, 104]
    creme, salt, milk = items
    assert creme.name == "Creme fraiche 38% fedt øko"
    assert creme.quantity == 2
    assert creme.bilka_article_number == "85164"
    assert creme.product is not None
    assert creme.product.price == Decimal("16.95")
    assert creme.product.store_name == "Bilka"
    assert salt.name == "Salt"
    assert salt.product is None
    assert salt.bilka_article_number is None
    assert milk.bilka_article_number is None


async def test_items_can_include_picked(logged_in: GomaClient) -> None:
    items = await logged_in.get_items(3, include_picked=True)

    picked = [item for item in items if item.is_picked]
    assert [(item.id, item.bilka_article_number) for item in picked] == [(102, "51138")]


async def test_expired_access_token_is_refreshed_and_the_rotated_token_saved(
    logged_in: GomaClient, goma: FakeGoma, storage: MemoryTokenStorage
) -> None:
    goma.now += goma.access_token_lifetime + 1
    goma.revoke_access_tokens()

    await logged_in.get_lists()

    assert goma.refreshes == 1
    assert storage.data is not None
    assert storage.data["refresh_token"] == "refresh-2"


async def test_a_token_rejected_before_its_expiry_is_refreshed_once_and_retried(
    logged_in: GomaClient, goma: FakeGoma
) -> None:
    goma.revoke_access_tokens()

    lists = await logged_in.get_lists()

    assert goma.refreshes == 1
    assert len(lists) == 2


async def test_a_dead_refresh_token_asks_for_login(logged_in: GomaClient, goma: FakeGoma) -> None:
    goma.revoke_access_tokens()
    goma.reject_refresh = True

    with pytest.raises(NotLoggedInError):
        await logged_in.get_lists()


async def test_session_survives_a_new_client(
    logged_in: GomaClient, goma: FakeGoma, storage: MemoryTokenStorage
) -> None:
    async with httpx.AsyncClient(transport=goma.transport()) as http:
        fresh = GomaClient(token_storage=storage, httpx_client=http)
        lists = await fresh.get_lists()

    assert len(lists) == 2


async def test_network_failure_is_reported_as_unreachable(storage: MemoryTokenStorage) -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as http:
        client = GomaClient(token_storage=storage, httpx_client=http)
        with pytest.raises(GomaUnreachableError):
            await client.request_code("someone@example.com")
