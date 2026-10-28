from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from goma import GomaClient, GomaError, ListItem, NotLoggedInError, ShoppingList

from .const import DOMAIN, LOGGER, UPDATE_INTERVAL

type GomaConfigEntry = ConfigEntry[GomaCoordinator]


@dataclass(frozen=True, slots=True)
class ListContents:
    shopping_list: ShoppingList
    items: list[ListItem]


class GomaCoordinator(DataUpdateCoordinator[dict[int, ListContents]]):
    """Polls every shopping list the account can see, keyed by list id."""

    config_entry: GomaConfigEntry

    def __init__(self, hass: HomeAssistant, entry: GomaConfigEntry, client: GomaClient) -> None:
        super().__init__(
            hass, LOGGER, config_entry=entry, name=DOMAIN, update_interval=UPDATE_INTERVAL
        )
        self.client = client

    async def _async_update_data(self) -> dict[int, ListContents]:
        try:
            return {
                shopping_list.id: ListContents(
                    shopping_list,
                    await self.client.get_items(shopping_list.id, include_picked=True),
                )
                for shopping_list in await self.client.get_lists()
            }
        except NotLoggedInError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        except GomaError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(err)},
            ) from err
