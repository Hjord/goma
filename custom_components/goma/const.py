from datetime import timedelta
from logging import getLogger

from homeassistant.const import Platform

LOGGER = getLogger(__package__)

DOMAIN = "goma"
PLATFORMS: list[Platform] = [Platform.TODO]

UPDATE_INTERVAL = timedelta(minutes=5)
