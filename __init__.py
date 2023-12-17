"""The Battery Automation integration."""
import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from .const import set_api_key_and_account, get_api_key_and_account
import voluptuous as vol
from homeassistant import config_entries
from .octopus_api import get_octopus_energy_rates
from .get_tariff import get_tariff
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    # Retrieve the API key and Account ID from the entry configuration & Battery capacity
    api_key = entry.data.get("api_key")
    account_id = entry.data.get("account_id")
    battery_charge_rate = entry.data.get("battery_charge_rate")
    battery_charge = entry.data.get("battery_charge")
    battery_capacity = entry.data.get("battery_capacity")
    charge_start = entry.data.get("charge_start")
    charge_end = entry.data.get("charge_end")
    #_LOGGER.info("battery cap: %s", battery_capacity)
    #_LOGGER.info("battery charge: %s", battery_charge)
    #_LOGGER.info("charge rate: %s", battery_charge_rate)
    # Store them in const.py for global access
        # Initialize DOMAIN key in hass.data if not already present
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    set_api_key_and_account(api_key, account_id)

    # Fetch tariff information
    tariff, product_code = await get_tariff(api_key, account_id)
    if not tariff or not product_code:
        _LOGGER.error("Failed to fetch tariff information.")
        return False

    # Define the rate types you want to fetch
    rate_types = [
        "rates_from_midnight",
        "afternoon_today",
        "afternoon_tomorrow",
        "all_rates",
        "current_import_rate",
        "rates_left",
    ]
    rates_data = {}

    for rate_type in rate_types:
        fetched_data = await get_octopus_energy_rates(api_key, account_id, rate_type)
        if fetched_data:
            rates_data[rate_type] = fetched_data

    if not rates_data:
        _LOGGER.error("Failed to fetch rates data. yellow")
        return False

    # Store the rates data in a way that your sensors can access it
    hass.data[DOMAIN]["rates_data"] = rates_data
    #_LOGGER.info("Rates Data:%s", rates_data)
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, Platform.SENSOR)
    )
    return True


# battery_entity = entry.data.get("battery_entity")
# battery_capacity = entry.data.get("battery_capacity")
