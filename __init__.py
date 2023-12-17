"""The Battery Automation integration."""
import logging
import asyncio
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from .const import set_api_key_and_account, get_api_key_and_account, DOMAIN
from .octopus_api import get_octopus_energy_rates
from .get_tariff import get_tariff

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    # Retrieve the API key, Account ID, and other config data
    api_key = entry.data.get("api_key")
    account_id = entry.data.get("account_id")
    battery_charge_rate = entry.data.get("battery_charge_rate")
    battery_charge_entity_id = entry.data.get("battery_charge")
    battery_capacity_entity_id = entry.data.get("battery_capacity")

    # Initialize domain data if not already done
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    # Store API key and Account ID for global access
    set_api_key_and_account(api_key, account_id)

    # Fetch tariff and rates data
    tariff, product_code = await get_tariff(api_key, account_id)
    if not tariff or not product_code:
        _LOGGER.error("Failed to fetch tariff information.")
        return False

    rate_types = ["rates_from_midnight", "afternoon_today", "afternoon_tomorrow", "all_rates", "current_import_rate", "rates_left"]
    rates_data = {}
    for rate_type in rate_types:
        fetched_data = await get_octopus_energy_rates(api_key, account_id, rate_type)
        if fetched_data:
            rates_data[rate_type] = fetched_data

    if not rates_data:
        _LOGGER.error("Failed to fetch rates data.")
        return False

    # Store rates data
    hass.data[DOMAIN]["rates_data"] = rates_data
    #_LOGGER.info("rates_data: %s", rates_data)


    # Wait for valid states of battery charge and capacity entities
    await wait_for_valid_state(hass, battery_charge_entity_id)
    await wait_for_valid_state(hass, battery_capacity_entity_id)

    # Wait for valid states of battery charge and capacity entities
    await wait_for_valid_state(hass, battery_charge_entity_id)
    await wait_for_valid_state(hass, battery_capacity_entity_id)

    # Store these states in global variables for sensor access
    battery_charge_state = float(hass.states.get(battery_charge_entity_id).state)
    battery_capacity_ah = float(hass.states.get(battery_capacity_entity_id).state)

    # Convert Ah to kWh and store in global variable
    hass.data[DOMAIN]["battery_capacity_kwh"] = battery_capacity_ah * 50 / 1000
    hass.data[DOMAIN]["battery_charge_state"] = battery_charge_state
    hass.data[DOMAIN]["battery_charge_rate"] = battery_charge_rate

    _LOGGER.info("Stored battery charge state in hass.data[DOMAIN]: %s", battery_charge_state)
    _LOGGER.info("Stored battery capacity state in hass.data[DOMAIN]: %s kWh", hass.data[DOMAIN]["battery_capacity_kwh"])
    _LOGGER.info("Stored battery charge rate in hass.data[DOMAIN]: %s", hass.data[DOMAIN]["battery_charge_rate"])





    # Forward to sensor setup
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, Platform.SENSOR)
    )
    return True

async def wait_for_valid_state(hass, entity_id):
    """Wait for a valid state of a given entity."""
    while True:
        state = hass.states.get(entity_id)
        if state and state.state not in ['unknown', 'unavailable', None]:
            try:
                float(state.state)  # Check if state is a valid number
                return state
            except ValueError:
                pass
        await asyncio.sleep(10)
