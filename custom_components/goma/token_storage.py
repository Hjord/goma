from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from goma import TokenStorage

from .const import DOMAIN

STORAGE_VERSION = 1


class HomeAssistantTokenStorage(TokenStorage):
    """Keeps the goma session in HA's private storage, one file per goma account.

    It is keyed by the goma user id rather than the config entry, because the login
    flow saves the session before the config entry exists.
    """

    def __init__(self, hass: HomeAssistant, user_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{user_id}.session", private=True
        )

    async def load(self) -> dict[str, Any] | None:
        return await self._store.async_load()

    async def save(self, data: dict[str, Any]) -> None:
        await self._store.async_save(data)

    async def async_remove(self) -> None:
        await self._store.async_remove()
