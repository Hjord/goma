import json
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs

import httpx

from goma.const import API_KEY

USER_ID = "00000000-0000-0000-0000-000000000001"


@dataclass
class FakeGoma:
    """An in-memory stand-in for goma's Supabase API, speaking the same HTTP."""

    code: str = "123456"
    lists: list[dict[str, Any]] = field(default_factory=list)
    items: list[dict[str, Any]] = field(default_factory=list)
    products: list[dict[str, Any]] = field(default_factory=list)
    primary_list_id: int | None = None
    access_token_lifetime: int = 3600
    now: float = 1_800_000_000.0
    codes_sent_to: list[dict[str, Any]] = field(default_factory=list)
    refreshes: int = 0
    reject_refresh: bool = False
    _issued: int = 0
    _valid_access: set[str] = field(default_factory=set)
    _valid_refresh: set[str] = field(default_factory=set)

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def revoke_access_tokens(self) -> None:
        self._valid_access.clear()

    def handle(self, request: httpx.Request) -> httpx.Response:
        if request.headers.get("apikey") != API_KEY:
            return httpx.Response(401, json={"message": "No API key found in request"})
        path = request.url.path
        if path == "/auth/v1/otp":
            self.codes_sent_to.append(json.loads(request.content))
            return httpx.Response(200, json={})
        if path == "/auth/v1/verify":
            body = json.loads(request.content)
            if body.get("token") != self.code or body.get("type") != "email":
                return httpx.Response(
                    403,
                    json={
                        "code": 403,
                        "error_code": "otp_expired",
                        "msg": "Token has expired or is invalid",
                    },
                )
            return httpx.Response(200, json=self._issue_session())
        if path == "/auth/v1/token":
            body = json.loads(request.content)
            if self.reject_refresh or body.get("refresh_token") not in self._valid_refresh:
                return httpx.Response(
                    400,
                    json={
                        "code": 400,
                        "error_code": "refresh_token_not_found",
                        "msg": "Invalid Refresh Token: Refresh Token Not Found",
                    },
                )
            self._valid_refresh.discard(body["refresh_token"])
            self.refreshes += 1
            return httpx.Response(200, json=self._issue_session())
        if path.startswith("/rest/v1/"):
            token = request.headers.get("authorization", "").removeprefix("Bearer ")
            if token not in self._valid_access:
                return httpx.Response(401, json={"code": "PGRST303", "message": "JWT expired"})
            return self._rest(path.removeprefix("/rest/v1/"), parse_qs(request.url.query.decode()))
        return httpx.Response(404)

    def _issue_session(self) -> dict[str, Any]:
        self._issued += 1
        access, refresh = f"access-{self._issued}", f"refresh-{self._issued}"
        self._valid_access.add(access)
        self._valid_refresh.add(refresh)
        return {
            "access_token": access,
            "token_type": "bearer",
            "expires_in": self.access_token_lifetime,
            "expires_at": int(self.now) + self.access_token_lifetime,
            "refresh_token": refresh,
            "user": {"id": USER_ID, "email": "someone@example.com"},
        }

    def _rest(self, table: str, query: dict[str, list[str]]) -> httpx.Response:
        if table == "shopping_lists":
            return httpx.Response(200, json=[row for row in self.lists if not row["deleted_at"]])
        if table == "user_preferences":
            return httpx.Response(200, json=[{"primary_shopping_list_id": self.primary_list_id}])
        if table == "shopping_list_items":
            list_id = int(query["shopping_list_id"][0].removeprefix("eq."))
            rows = [
                r for r in self.items if r["shopping_list_id"] == list_id and not r["is_hidden"]
            ]
            if query.get("is_picked") == ["eq.false"]:
                rows = [r for r in rows if not r["is_picked"]]
            return httpx.Response(200, json=rows)
        if table == "product_search_view":
            listed = query["product_id"][0].removeprefix("in.(").removesuffix(")").split(",")
            wanted = [product_id.strip('"') for product_id in listed]
            return httpx.Response(200, json=[p for p in self.products if p["product_id"] in wanted])
        return httpx.Response(404, json={"message": f"relation {table} does not exist"})
