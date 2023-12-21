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
from homeassistant.const import EVENT_STATE_CHANGED


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
    ac_charge_entity_id = entry.data.get("ac_charge")
    _LOGGER.info("AC charge entity id: %s", ac_charge_entity_id)

    # Initialize domain data if not already done
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {
            "charging_control_enabled": False,
            "custom_soc_percentage": 0,
            "charging_status_sensor": None,
        }
    hass.data[DOMAIN]["ac_charge_entity_id"] = ac_charge_entity_id

    # Store API key and Account ID for global access
    set_api_key_and_account(api_key, account_id)

    # Fetch tariff and rates data
    tariff, product_code = await get_tariff(api_key, account_id)
    if not tariff or not product_code:
        _LOGGER.error("Failed to fetch tariff information.")
        return False

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
        _LOGGER.error("Failed to fetch rates data.")
        return False

    # Store rates data
    hass.data[DOMAIN]["rates_data"] = rates_data
    #_LOGGER.info('Rates Data: %s', rates_data)

    # Wait for valid states of battery charge and capacity entities
    await wait_for_valid_state(hass, battery_charge_entity_id)
    await wait_for_valid_state(hass, battery_capacity_entity_id)


    # Store states in global variables for sensor access
    battery_charge_state = float(hass.states.get(battery_charge_entity_id).state)
    battery_capacity_ah = float(hass.states.get(battery_capacity_entity_id).state)
    ac_charge_state = hass.states.get(ac_charge_entity_id).state
    _LOGGER.info("AC charge swith state:%s", ac_charge_state)


    # Convert Ah to kWh and store in global variable
    hass.data[DOMAIN]["battery_capacity_kwh"] = battery_capacity_ah * 50 / 1000
    hass.data[DOMAIN]["battery_charge_state"] = battery_charge_state
    hass.data[DOMAIN]["battery_charge_rate"] = battery_charge_rate

    charging_entity_start = entry.data.get("charge_start")
    charging_entity_end = entry.data.get("charge_end")
    hass.data[DOMAIN]["charging_control"] = ChargingControl(
        hass, charging_entity_start, charging_entity_end
    )
    # Forward to sensor and switch setup
    await hass.config_entries.async_forward_entry_setup(entry, Platform.SENSOR)

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, Platform.SWITCH)
    )
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, Platform.NUMBER)
    )

    # Reference the update_charge_plan function from sensor.py
    update_charge_plan = hass.data[DOMAIN]["update_charge_plan"]

    # Event listener for battery charge state and custom_soc_percentage changes
    async def state_change_listener(event):
        """Handle state changes for entities."""
        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")

        # Using the global value for battery charge state
        if entity_id == hass.data[DOMAIN].get("battery_charge_state"):
            _LOGGER.info("init abc battery charge:%s", battery_charge_state)
            if (
                old_state is not None
                and abs(float(new_state.state) - float(old_state.state)) > 5
            ):
                await update_charge_plan()

        # Using the domain value for custom_soc_percentage
        elif entity_id == hass.data[DOMAIN].get("custom_soc_percentage_entity_id"):
            if new_state.state is not None and old_state.state != new_state.state:
                await update_charge_plan()

    hass.bus.async_listen(EVENT_STATE_CHANGED, state_change_listener)

    return True


async def wait_for_valid_state(hass, entity_id):
    """Wait for a valid state of a given entity."""
    while True:
        state = hass.states.get(entity_id)
        if state and state.state not in ["unknown", "unavailable", None]:
            try:
                float(state.state)  # Check if state is a valid number
                return state
            except ValueError:
                pass
        await asyncio.sleep(10)
