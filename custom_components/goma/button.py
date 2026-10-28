from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import GomaConfigEntry, GomaCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GomaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([GomaRefreshButton(entry.runtime_data)])


class GomaRefreshButton(CoordinatorEntity[GomaCoordinator], ButtonEntity):
    """Reads the goma lists now instead of waiting for the next update."""

    _attr_has_entity_name = True
    _attr_translation_key = "refresh"

    def __init__(self, coordinator: GomaCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.unique_id}_refresh"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        return True

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()
