"""The Battery Automation integration."""
import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from .const import set_api_key_and_account

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up the Battery Automation integration from a config entry."""
    _LOGGER.info("Setting up Battery Automation integration.")

    # Retrieve the API key and Account ID from the entry configuration
    api_key = entry.data.get("api_key")
    account_id = entry.data.get("account_id")
    battery_sensor = entry.data.get("battery_sensor")

    # Store them in const.py for global access
    set_api_key_and_account(api_key, account_id)

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, Platform.SENSOR)
    )
    return True
