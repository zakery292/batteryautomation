"""The Battery Automation integration."""
# __init__.py
import logging
import asyncio
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from .const import DOMAIN, set_api_key_and_account
from .octopus_api import get_octopus_energy_rates
from .get_tariff import get_tariff
from .charging_control import ChargingControl
from .sensor import BatteryChargePlanSensor
from .switch import ChargingControlSwitchEntity

_LOGGER = logging.getLogger(__name__)

def set_charging_control_enabled(hass: HomeAssistant, value: bool):
    """Set the state of the charging control."""
    hass.data[DOMAIN]["charging_control_enabled"] = value

def get_charging_control_enabled(hass: HomeAssistant) -> bool:
    """Get the state of the charging control."""
    return hass.data[DOMAIN].get("charging_control_enabled", False)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    # Retrieve the API key, Account ID, and other config data
    api_key = entry.data.get("api_key")
    account_id = entry.data.get("account_id")
    battery_charge_rate = entry.data.get("battery_charge_rate")
    battery_charge_entity_id = entry.data.get("battery_charge")
    battery_capacity_entity_id = entry.data.get("battery_capacity")

    # Initialize domain data if not already done
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {"charging_control_enabled": False}

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

    # Wait for valid states of battery charge and capacity entities
    await wait_for_valid_state(hass, battery_charge_entity_id)
    await wait_for_valid_state(hass, battery_capacity_entity_id)

    # Store states in global variables for sensor access
    battery_charge_state = float(hass.states.get(battery_charge_entity_id).state)
    battery_capacity_ah = float(hass.states.get(battery_capacity_entity_id).state)

    # Convert Ah to kWh and store in global variable
    hass.data[DOMAIN]["battery_capacity_kwh"] = battery_capacity_ah * 50 / 1000
    hass.data[DOMAIN]["battery_charge_state"] = battery_charge_state
    hass.data[DOMAIN]["battery_charge_rate"] = battery_charge_rate

    charging_entity_start = entry.data.get("charge_start")
    charging_entity_end = entry.data.get("charge_end")
    hass.data[DOMAIN]["charging_control"] = ChargingControl(hass, charging_entity_start, charging_entity_end)


    # Forward to sensor and switch setup
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, Platform.SENSOR)
    )
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, Platform.SWITCH)
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

# ... other necessary functions and classes ...
