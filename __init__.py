"""The Battery Automation integration."""
# __init__.py
import logging
import asyncio
from .battery_soc_collection import init_database, collect_soc_data
from .sensors.average_battery_usage import AverageBatteryUsageSensor
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.helpers.event import async_track_time_interval
from .const import DOMAIN, set_api_key_and_account
from .octopus_api import get_octopus_energy_rates
from .get_tariff import get_tariff
from .charging_control import ChargingControl
from homeassistant.const import EVENT_STATE_CHANGED
from datetime import datetime, time, timedelta
from .sensors.octopus_energy_sensor import OctopusEnergySensor
from .sensors.battery_charge_plan_sensor import BatteryChargePlanSensor
from .sensor import ChargingStatusSensor
from homeassistant.helpers.event import async_call_later

_LOGGER = logging.getLogger(__name__)

SOC_DATA = {}  # Dictionary to store SoC data
MAX_DATA_AGE = timedelta(days=7)  # Maximum age of data to keep


def set_charging_control_enabled(hass: HomeAssistant, value: bool):
    """Set the state of the charging control."""
    hass.data[DOMAIN]["charging_control_enabled"] = value


def get_charging_control_enabled(hass: HomeAssistant) -> bool:
    """Get the state of the charging control."""
    return hass.data[DOMAIN].get("charging_control_enabled", False)


# Define the function that schedules updates
# Function to calculate the time until the next desired update time
def time_until_next_update(update_times):
    now = datetime.now()
    today_times = [datetime.combine(now.date(), t) for t in update_times]
    future_times = [t for t in today_times if t > now]
    next_time = min(future_times, default=today_times[0] + timedelta(days=1))
    return (next_time - now).total_seconds()


def setup_scheduled_updates(hass):
    def trigger_update():
        _LOGGER.info("Triggering charge plan update")
        hass.bus.async_fire("battery_charge_plan_update")
        setup_next_call()

    async def async_trigger_update():
        trigger_update()

    def setup_next_call():
        seconds_until_next = time_until_next_update(
            [time(11, 30), time(17, 51), time(23, 30)]
        )
        _LOGGER.info(f"Scheduling next update in {seconds_until_next} seconds.")
        async_call_later(
            hass,
            seconds_until_next,
            lambda _: hass.async_create_task(async_trigger_update()),
        )

    setup_next_call()


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
    hass.data[DOMAIN]["battery_charge_entity_id"] = entry.data.get("battery_charge")

    # Store API key and Account ID for global access
    set_api_key_and_account(api_key, account_id)

    # Start tariff fetching as a background task
    hass.async_create_task(get_tariff_background(api_key, account_id, hass))

    await wait_for_valid_state(hass, battery_charge_entity_id)
    await wait_for_valid_state(hass, battery_capacity_entity_id)
    # Call the setup_scheduled_updates at the end of async_setup_entry
    setup_scheduled_updates(hass)
    # Initialize the database
    init_database(hass)

    # Schedule the collect_soc_data function to run every 10 minutes
    async def interval_callback(now):
        await collect_soc_data(hass)

    async_track_time_interval(hass, interval_callback, timedelta(minutes=1))

    ## Battery Sensor updates ###
    async def update_sensors(now):
        sensor_entities = hass.data[DOMAIN].get("average_battery_usage_sensors", [])
        for sensor in sensor_entities:
            await sensor.async_update()

    async_track_time_interval(hass, update_sensors, timedelta(minutes=1))

    async def update_sensors(now):
        sensor_entities = hass.data[DOMAIN].get("average_battery_usage_sensors", [])
        for sensor in sensor_entities:
            # Check if the sensor is not an instance of ChargingStatusSensor
            if not isinstance(sensor, ChargingStatusSensor):
                await sensor.async_update()

    # Store states in global variables for sensor access
    battery_charge_state = float(hass.states.get(battery_charge_entity_id).state)
    battery_capacity_ah = float(hass.states.get(battery_capacity_entity_id).state)
    # _LOGGER.info("AC charge swith state:%s", ac_charge_state)

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

    # Schedule the periodic rate update task
    async def periodic_rate_update(api_key, account_id, hass):
        """Periodically update rates data at around 4:10 PM."""
        while True:
            now = datetime.now()

            # Calculate next occurrence of 4:10 PM
            next_update_time = datetime.combine(now.date(), time(16, 00))
            if now > next_update_time:
                next_update_time += timedelta(days=1)

            # Sleep until it's time to fetch new rates data
            await asyncio.sleep((next_update_time - now).total_seconds())

            try:
                # Fetch new rates data
                for rate_type in [
                    "rates_from_midnight",
                    "afternoon_today",
                    "evening_today" "afternoon_tomorrow",
                    "all_rates",
                    "current_import_rate",
                    "rates_left",
                ]:
                    fetched_data = await get_octopus_energy_rates(
                        api_key, account_id, rate_type
                    )
                    if fetched_data:
                        hass.data[DOMAIN]["rates_data"][rate_type] = fetched_data

                hass.data[DOMAIN]["rates_data"]["last_update"] = datetime.now()
                _LOGGER.info("Rates data updated.")

                # Trigger updates for each OctopusEnergySensor
                for sensor in hass.data[DOMAIN]["sensors"]:
                    if isinstance(sensor, OctopusEnergySensor):
                        await sensor.async_update()

            except Exception as e:
                _LOGGER.error(f"Error during periodic rate update: {e}")
                # Wait a while before retrying to prevent spamming in case of persistent errors
                await asyncio.sleep(60 * 5)  # Retry after 5 minutes

    hass.loop.create_task(periodic_rate_update(api_key, account_id, hass))
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

    # Schedule local rates data update task

    async def local_rates_update():
        while True:
            update_local_rates_data(hass)
            # Calculate wait time until next half-hour mark
            now = datetime.now()
            seconds_until_next_update = (30 - now.minute % 30) * 60 - now.second
            _LOGGER.info(
                f"Seconds till next update {seconds_until_next_update} from init.py"
            )
            await asyncio.sleep(seconds_until_next_update)

    async def start_local_rates_update(event):
        hass.loop.create_task(local_rates_update())

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, start_local_rates_update)

    return True


def update_local_rates_data(hass):
    """Update local rates data based on the current time."""
    now = datetime.now()

    # Update current_import_rate
    all_rates = hass.data[DOMAIN]["rates_data"].get("all_rates", [])
    current_import_rate = next(
        (
            rate
            for rate in all_rates
            if datetime.strptime(
                f"{rate['Date']} {rate['Start Time']}", "%d-%m-%Y %H:%M:%S"
            )
            <= now
            < datetime.strptime(
                f"{rate['Date']} {rate['End Time']}", "%d-%m-%Y %H:%M:%S"
            )
        ),
        None,
    )
    if current_import_rate:
        # Ensuring current_import_rate is a list with a single dictionary
        hass.data[DOMAIN]["rates_data"]["current_import_rate"] = [current_import_rate]
        _LOGGER.info(f"Updated current import rate: {current_import_rate}")

    # Update rates_left
    rates_left = [
        rate
        for rate in all_rates
        if datetime.strptime(
            f"{rate['Date']} {rate['Start Time']}", "%d-%m-%Y %H:%M:%S"
        )
        > now
    ]
    hass.data[DOMAIN]["rates_data"]["rates_left"] = rates_left
    _LOGGER.info(f"Updated rates left: {rates_left}")

    _LOGGER.info("Local rates data updated.")
    for sensor in hass.data[DOMAIN].get("sensors", []):
        if isinstance(sensor, OctopusEnergySensor):
            hass.create_task(sensor.async_refresh())

    _LOGGER.info("Local rates data updated and sensor updates triggered.")


async def get_tariff_background(api_key, account_id, hass):
    """Background task for fetching tariff."""
    try:
        tariff, product_code = await get_tariff(api_key, account_id)
        if tariff and product_code:
            hass.data[DOMAIN]["tariff"] = tariff
            hass.data[DOMAIN]["product_code"] = product_code

            rate_types = [
                "rates_from_midnight",
                "afternoon_today",
                "evening_today",
                "afternoon_tomorrow",
                "all_rates",
                "current_import_rate",
                "rates_left",
            ]
            rates_data = {}
            for rate_type in rate_types:
                fetched_data = await get_octopus_energy_rates(
                    api_key, account_id, rate_type
                )
                if fetched_data:
                    rates_data[rate_type] = fetched_data

            if rates_data:
                hass.data[DOMAIN]["rates_data"] = rates_data
            else:
                _LOGGER.error("Failed to fetch rates data.")
        else:
            _LOGGER.error("Failed to fetch tariff information.")
    except Exception as e:
        _LOGGER.error(f"Error fetching tariff information: {e}")


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
