from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from goma import GomaClient, GomaError, ListItem, NotLoggedInError, ShoppingList

from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MINUTES, DOMAIN, LOGGER

type GomaConfigEntry = ConfigEntry[GomaCoordinator]


@dataclass(frozen=True, slots=True)
class ListContents:
    shopping_list: ShoppingList
    items: list[ListItem]


class GomaCoordinator(DataUpdateCoordinator[dict[int, ListContents]]):
    """Polls every shopping list the account can see, keyed by list id."""

    config_entry: GomaConfigEntry

    def __init__(self, hass: HomeAssistant, entry: GomaConfigEntry, client: GomaClient) -> None:
        minutes = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MINUTES)
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=minutes),
        )
        self.client = client
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="goma",
            entry_type=DeviceEntryType.SERVICE,
        )

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
