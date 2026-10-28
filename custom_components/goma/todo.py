from homeassistant.components.todo import TodoItem, TodoItemStatus, TodoListEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from goma import ListItem

from .coordinator import GomaConfigEntry, GomaCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GomaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    known: set[int] = set()

    @callback
    def add_new_lists() -> None:
        new = [list_id for list_id in coordinator.data if list_id not in known]
        known.update(new)
        async_add_entities(GomaTodoList(coordinator, list_id) for list_id in new)

    add_new_lists()
    entry.async_on_unload(coordinator.async_add_listener(add_new_lists))


class GomaTodoList(CoordinatorEntity[GomaCoordinator], TodoListEntity):
    """A goma shopping list, read-only. Ticked-off items show as completed."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: GomaCoordinator, list_id: int) -> None:
        super().__init__(coordinator)
        self._list_id = list_id
        self._attr_unique_id = f"{coordinator.config_entry.unique_id}_{list_id}"
        self._attr_device_info = coordinator.device_info

    @property
    def name(self) -> str | None:
        contents = self.coordinator.data.get(self._list_id)
        return contents.shopping_list.name if contents else None

    @property
    def available(self) -> bool:
        return super().available and self._list_id in self.coordinator.data

    @property
    def todo_items(self) -> list[TodoItem] | None:
        contents = self.coordinator.data.get(self._list_id)
        if contents is None:
            return None
        return [todo_item(item) for item in contents.items]


def todo_item(item: ListItem) -> TodoItem:
    summary = item.name if item.quantity == 1 else f"{item.quantity} x {item.name}"
    details = [
        part
        for part in (
            item.product.brand if item.product else None,
            item.product.store_name if item.product else None,
        )
        if part
    ]
    return TodoItem(
        uid=str(item.id),
        summary=summary,
        status=TodoItemStatus.COMPLETED if item.is_picked else TodoItemStatus.NEEDS_ACTION,
        description=" · ".join(details) or None,
    )
