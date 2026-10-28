import importlib.util
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest

from goma import GomaClient, TokenStorage

from .fake_goma import FakeGoma

# The Home Assistant tests need the `ha` dependency group; the library tests run without it.
collect_ignore = [] if importlib.util.find_spec("homeassistant") else ["ha"]


class MemoryTokenStorage(TokenStorage):
    def __init__(self) -> None:
        self.data: dict[str, Any] | None = None

    async def load(self) -> dict[str, Any] | None:
        return self.data

    async def save(self, data: dict[str, Any]) -> None:
        self.data = data


@pytest.fixture
def goma() -> FakeGoma:
    return FakeGoma(
        lists=[
            {
                "id": 7,
                "name": "Weekend",
                "user_id": "u",
                "group_id": None,
                "created_at": "2026-10-02T10:00:00+00:00",
                "deleted_at": None,
            },
            {
                "id": 3,
                "name": "Indkøbsliste",
                "user_id": "u",
                "group_id": "g-1",
                "created_at": "2026-08-18T06:49:18+00:00",
                "deleted_at": None,
            },
            {
                "id": 9,
                "name": "Gammel",
                "user_id": "u",
                "group_id": None,
                "created_at": "2026-01-01T00:00:00+00:00",
                "deleted_at": "2026-02-01T00:00:00+00:00",
            },
        ],
        primary_list_id=3,
        items=[
            {
                "id": 101,
                "shopping_list_id": 3,
                "product_id": "bilka-85164",
                "quantity": 2,
                "is_picked": False,
                "is_hidden": False,
                "custom_name": None,
                "recipe_id": "r-1",
            },
            {
                "id": 102,
                "shopping_list_id": 3,
                "product_id": "bilka-51138",
                "quantity": 1,
                "is_picked": True,
                "is_hidden": False,
                "custom_name": None,
                "recipe_id": None,
            },
            {
                "id": 103,
                "shopping_list_id": 3,
                "product_id": None,
                "quantity": 1,
                "is_picked": False,
                "is_hidden": False,
                "custom_name": "Salt",
                "recipe_id": None,
            },
            {
                "id": 104,
                "shopping_list_id": 3,
                "product_id": "netto-4242",
                "quantity": 1,
                "is_picked": False,
                "is_hidden": False,
                "custom_name": None,
                "recipe_id": None,
            },
            {
                "id": 105,
                "shopping_list_id": 3,
                "product_id": "bilka-20015",
                "quantity": 1,
                "is_picked": False,
                "is_hidden": True,
                "custom_name": None,
                "recipe_id": None,
            },
            {
                "id": 201,
                "shopping_list_id": 7,
                "product_id": "bilka-37998",
                "quantity": 1,
                "is_picked": False,
                "is_hidden": False,
                "custom_name": None,
                "recipe_id": None,
            },
        ],
        products=[
            {
                "product_id": "bilka-85164",
                "product_name": "Creme fraiche 38% fedt øko",
                "brand": "Salling ØKO",
                "store_name": "Bilka",
                "current_price": 16.95,
                "amount": 200.0,
                "unit": "g",
            },
            {
                "product_id": "bilka-51138",
                "product_name": "Kartofler",
                "brand": "Salling",
                "store_name": "Bilka",
                "current_price": 18,
                "amount": 2.0,
                "unit": "kg",
            },
            {
                "product_id": "netto-4242",
                "product_name": "Mælk",
                "brand": "Arla",
                "store_name": "Netto",
                "current_price": 12.5,
                "amount": 1.0,
                "unit": "l",
            },
        ],
    )


@pytest.fixture
def storage() -> MemoryTokenStorage:
    return MemoryTokenStorage()


@pytest.fixture
def clock(goma: FakeGoma, monkeypatch: pytest.MonkeyPatch) -> FakeGoma:
    monkeypatch.setattr("goma.client.time.time", lambda: goma.now)
    return goma


@pytest.fixture
async def client(
    goma: FakeGoma, storage: MemoryTokenStorage, clock: FakeGoma
) -> AsyncIterator[GomaClient]:
    async with httpx.AsyncClient(transport=goma.transport()) as http:
        yield GomaClient(token_storage=storage, httpx_client=http)


@pytest.fixture
async def logged_in(client: GomaClient, goma: FakeGoma) -> GomaClient:
    await client.request_code("someone@example.com")
    await client.verify_code("someone@example.com", goma.code)
    return client
