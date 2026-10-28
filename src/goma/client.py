import time
from types import TracebackType
from typing import Any, Self

import httpx

from .const import API_BASE_URL, API_KEY, TOKEN_RENEWAL_MARGIN_SECONDS
from .exceptions import (
    GomaError,
    GomaUnreachableError,
    InvalidCodeError,
    NotLoggedInError,
    UnexpectedResponseError,
)
from .models import ListItem, Product, Session, ShoppingList
from .token_storage import TokenStorage

ITEM_FIELDS = "id,product_id,quantity,is_picked,custom_name,recipe_id"
PRODUCT_FIELDS = "product_id,product_name,brand,store_name,current_price,amount,unit"


class GomaClient:
    """Reads goma.gg shopping lists as the logged-in user.

    Logging in takes two steps, because goma only offers a 6-digit email code:
    `request_code(email)`, then `verify_code(email, code)`. The session is kept in
    `token_storage` and renewed on its own; `NotLoggedInError` means it has to be redone.
    """

    def __init__(
        self,
        *,
        token_storage: TokenStorage | None = None,
        httpx_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._storage = token_storage
        self._http = httpx_client or httpx.AsyncClient(timeout=20)
        self._owns_http = httpx_client is None
        self._session: Session | None = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    async def request_code(self, email: str) -> None:
        """Ask goma to email a login code. Never creates an account."""
        response = await self._send(
            "POST", "/auth/v1/otp", json={"email": email, "create_user": False}
        )
        if response.status_code != 200:
            raise GomaError(f"goma refused to send a code: {_message(response)}")

    async def verify_code(self, email: str, code: str) -> str:
        """Log in with the emailed code. Returns the goma user id."""
        response = await self._send(
            "POST",
            "/auth/v1/verify",
            json={"type": "email", "email": email, "token": code.strip()},
        )
        if response.status_code in (400, 403):
            raise InvalidCodeError(_message(response))
        session = Session.from_auth(_json(response, "Login"))
        await self._store(session)
        return session.user_id

    async def get_lists(self) -> list[ShoppingList]:
        """Every shopping list the account can see, newest first."""
        rows = await self._rest(
            "shopping_lists", {"select": "id,name,group_id,deleted_at", "order": "created_at.desc"}
        )
        prefs = await self._rest("user_preferences", {"select": "primary_shopping_list_id"})
        primary = prefs[0].get("primary_shopping_list_id") if prefs else None
        return [
            ShoppingList(
                id=row["id"],
                name=row["name"],
                group_id=row.get("group_id"),
                is_primary=row["id"] == primary,
            )
            for row in rows
            if not row.get("deleted_at")
        ]

    async def get_items(self, list_id: int, *, include_picked: bool = False) -> list[ListItem]:
        """The list's items, with goma's product details where it has a product."""
        params = {
            "select": ITEM_FIELDS,
            "shopping_list_id": f"eq.{list_id}",
            "is_hidden": "eq.false",
            "order": "id.asc",
        }
        if not include_picked:
            params["is_picked"] = "eq.false"
        rows = await self._rest("shopping_list_items", params)
        products = await self._products({row["product_id"] for row in rows if row["product_id"]})
        return [ListItem.from_row(row, products.get(row["product_id"])) for row in rows]

    async def _products(self, product_ids: set[str]) -> dict[str, Product]:
        if not product_ids:
            return {}
        quoted = ",".join(f'"{product_id}"' for product_id in sorted(product_ids))
        rows = await self._rest(
            "product_search_view", {"select": PRODUCT_FIELDS, "product_id": f"in.({quoted})"}
        )
        return {row["product_id"]: Product.from_row(row) for row in rows}

    async def _rest(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        session = await self._valid_session()
        response = await self._rest_request(table, params, session)
        if response.status_code == 401:
            response = await self._rest_request(table, params, await self._refresh(session))
        if response.status_code == 401:
            raise NotLoggedInError("goma rejected a freshly renewed session")
        data = _json(response, table)
        if not isinstance(data, list):
            raise UnexpectedResponseError(f"{table} did not answer with rows")
        return data

    async def _rest_request(
        self, table: str, params: dict[str, str], session: Session
    ) -> httpx.Response:
        return await self._send(
            "GET",
            f"/rest/v1/{table}",
            params=params,
            headers={"Authorization": f"Bearer {session.access_token}"},
        )

    async def _valid_session(self) -> Session:
        if self._session is None and self._storage:
            stored = await self._storage.load()
            self._session = Session.from_stored(stored) if stored else None
        if self._session is None:
            raise NotLoggedInError("Not logged in to goma")
        if self._session.expires_at - TOKEN_RENEWAL_MARGIN_SECONDS <= time.time():
            return await self._refresh(self._session)
        return self._session

    async def _refresh(self, session: Session) -> Session:
        response = await self._send(
            "POST",
            "/auth/v1/token",
            params={"grant_type": "refresh_token"},
            json={"refresh_token": session.refresh_token},
        )
        if response.status_code in (400, 401, 403):
            raise NotLoggedInError(f"goma ended the session: {_message(response)}")
        renewed = Session.from_auth(_json(response, "Session renewal"))
        await self._store(renewed)
        return renewed

    async def _store(self, session: Session) -> None:
        self._session = session
        if self._storage:
            await self._storage.save(session.to_stored())

    async def _send(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        headers = {"apikey": API_KEY, **kwargs.pop("headers", {})}
        try:
            return await self._http.request(
                method, f"{API_BASE_URL}{path}", headers=headers, **kwargs
            )
        except httpx.TransportError as err:
            raise GomaUnreachableError(f"Could not reach goma: {err}") from err


def _json(response: httpx.Response, what: str) -> Any:
    if response.status_code != 200:
        raise UnexpectedResponseError(f"{what} failed with HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError:
        raise UnexpectedResponseError(f"{what} did not answer with JSON") from None


def _message(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return f"HTTP {response.status_code}"
    return data.get("msg") or data.get("message") or f"HTTP {response.status_code}"
