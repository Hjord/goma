from homeassistant.components.todo import DOMAIN as TODO_DOMAIN
from homeassistant.core import HomeAssistant, SupportsResponse, callback
from homeassistant.helpers import service

from .const import DOMAIN


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        "get_items",
        entity_domain=TODO_DOMAIN,
        schema=None,
        func="async_get_goma_items",
        supports_response=SupportsResponse.ONLY,
    )
