from logging import getLogger

from homeassistant.const import Platform

LOGGER = getLogger(__package__)

DOMAIN = "goma"
PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.TODO]

CONF_UPDATE_INTERVAL = "update_interval"
DEFAULT_UPDATE_INTERVAL_MINUTES = 60
