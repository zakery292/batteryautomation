"""The Battery Automation integration."""
import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from .const import set_api_key_and_account, set_battery_capacity
import voluptuous as vol
from homeassistant import config_entries


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up the Octopus rates from a config entry."""
    _LOGGER.info("Setting up Octopus rates")

    # Retrieve the API key and Account ID from the entry configuration & Battery capacity
    api_key = entry.data.get("api_key")
    account_id = entry.data.get("account_id")
    battery_charge_rate = entry.data.get("battery_charge_rate")
    battery_charge = entry.data.get("battery_charge")
    battery_capacity = entry.data.get("battery_capacity")
    charge_start = entry.data.get("charge_start")
    charge_end = entry.data.get("charge_end")
    _LOGGER.info("battery cap: %s", battery_capacity)
    # Store them in const.py for global access
    set_api_key_and_account(api_key, account_id)

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, Platform.SENSOR)
    )
    return True





# battery_entity = entry.data.get("battery_entity")
# battery_capacity = entry.data.get("battery_capacity")
