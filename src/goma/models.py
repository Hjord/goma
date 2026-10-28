import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .const import BILKA_PRODUCT_PREFIX


@dataclass(frozen=True, slots=True)
class Session:
    access_token: str
    refresh_token: str
    expires_at: int
    user_id: str

    @classmethod
    def from_auth(cls, data: dict[str, Any]) -> "Session":
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=int(data["expires_at"]),
            user_id=data["user"]["id"],
        )

    @classmethod
    def from_stored(cls, data: dict[str, Any]) -> "Session | None":
        try:
            return cls(
                access_token=data["access_token"],
                refresh_token=data["refresh_token"],
                expires_at=int(data["expires_at"]),
                user_id=data["user_id"],
            )
        except (KeyError, TypeError, ValueError):
            return None

    def to_stored(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "user_id": self.user_id,
        }


@dataclass(frozen=True, slots=True)
class ShoppingList:
    id: int
    name: str
    group_id: str | None
    is_primary: bool


@dataclass(frozen=True, slots=True)
class Product:
    product_id: str
    name: str
    brand: str | None
    store_name: str | None
    price: Decimal | None
    amount: Decimal | None
    unit: str | None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Product":
        return cls(
            product_id=row["product_id"],
            name=row.get("product_name") or row["product_id"],
            brand=row.get("brand"),
            store_name=row.get("store_name"),
            price=_decimal(row.get("current_price")),
            amount=_decimal(row.get("amount")),
            unit=row.get("unit"),
        )


@dataclass(frozen=True, slots=True)
class ListItem:
    id: int
    quantity: int
    is_picked: bool
    product_id: str | None
    custom_name: str | None
    recipe_id: str | None
    product: Product | None

    @classmethod
    def from_row(cls, row: dict[str, Any], product: Product | None) -> "ListItem":
        return cls(
            id=row["id"],
            # Bilka's cart takes whole units; a fractional goma quantity rounds up.
            quantity=math.ceil(row.get("quantity") or 1),
            is_picked=bool(row.get("is_picked")),
            product_id=row.get("product_id"),
            custom_name=row.get("custom_name"),
            recipe_id=row.get("recipe_id"),
            product=product,
        )

    @property
    def name(self) -> str:
        if self.product:
            return self.product.name
        return self.custom_name or self.product_id or f"item {self.id}"

    @property
    def bilka_article_number(self) -> str | None:
        """The BilkaToGo Article Number, for products goma found at Bilka."""
        if self.product_id and self.product_id.startswith(BILKA_PRODUCT_PREFIX):
            return self.product_id.removeprefix(BILKA_PRODUCT_PREFIX)
        return None


def _decimal(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))
