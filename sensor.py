"""Define sensors for Battery Automation."""
# sensor.py
import logging
from homeassistant.helpers.entity import Entity
from .octopus_api import get_octopus_energy_rates, rates_data
from .const import (get_api_key_and_account, DOMAIN, unique_id_charge_plan_sensor, unique_id_battery_sensor, unique_id_charging_status)
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta
import asyncio
import math
from .charging_control import ChargingControl
SCAN_INTERVAL = timedelta(minutes=30)  # Set the desired interval
_LOGGER = logging.getLogger(__name__)

#### Octopus Rates below #####
async def update_charge_plan(hass):
    """Function to update the charge plan sensor."""
    charge_plan_sensor = next((sensor for sensor in hass.data[DOMAIN]["sensors"] if isinstance(sensor, BatteryChargePlanSensor)), None)
    if charge_plan_sensor:
        await charge_plan_sensor.async_update()

class OctopusEnergySensor(Entity):
    def __init__(self, name, rate_type):
        self._name = name
        self._rate_type = rate_type
        self._state = None
        self._attributes = {}
        self._api_key, self._account_id = get_api_key_and_account()

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} Octopus Energy"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        return self._attributes

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return f"{self._account_id}_{self._name}"

    @property
    def device_info(self):
        """Return information about the device this sensor is part of."""
        return {
            "identifiers": {(DOMAIN, self._account_id)},
            "name": "Octopus Energy",
            "manufacturer": "Zakery292",
        }
    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return "mdi:clock"

    @property
    def available(self):
        """Return True if the sensor is available."""
        return self._state is not None

    @property
    def should_poll(self):
        """Return the polling state."""
        return True

    async def async_update(self):
        """Fetch new state data for the sensor."""
        try:
            rates = self.hass.data[DOMAIN]["rates_data"].get(self._rate_type, [])
            if rates:
                self._state = "Data Available"
                self._attributes["rates"] = rates
            else:
                self._state = "No Data"
                self._attributes = {}
        except Exception as e:
            _LOGGER.error(f"Error updating Octopus Energy data: {e}")
            self._state = "Error"
            self._attributes = {}


##### Battery Storage Sensors below #####

class BatteryStorageSensors(Entity):
    def __init__(self, name, sensor_type):
        self._name = name
        self._sensor_type = sensor_type
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} Sensor"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return f"{unique_id_battery_sensor}_{self._name}_{self._sensor_type}"

    @property
    def device_info(self):
        """Return information about the device this sensor is part of."""
        return {
            "identifiers": {(DOMAIN, "battery_storage_sensors")},
            "name": "Battery Storage Automation",
            "manufacturer": "Zakery292",
        }

    @property
    def should_poll(self):
        """Return the polling state."""
        return True

    async def async_update(self):
        try:
            # Using global variable for battery capacity in kWh
            battery_capacity_kwh = self.hass.data[DOMAIN]["battery_capacity_kwh"]
            _LOGGER.info("battery capacity kWh: %s", battery_capacity_kwh)
            if battery_capacity_kwh is None:
                self._state = "Unavailable"
            else:
                self._state = battery_capacity_kwh
        except Exception as e:
            _LOGGER.error(f"Error updating Battery Capacity: {e}")
            self._state = "Error"

class BatteryChargePlanSensor(Entity):
    def __init__(self, name):
        self._name = name
        self._state = None
        self._attributes = {}

    async def async_added_to_hass(self):
        self.hass.bus.async_listen("custom_slider_value_changed_event", self.handle_slider_change)


    async def handle_slider_change(self, event):
        _LOGGER.info("Detected slider change in BatteryChargePlanSensor.")
        await self.async_update()

    @property
    def name(self):
        return f"{self._name} Charge Plan"

    @property
    def state(self):
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return "mdi:battery-charging"

    @property
    def device_info(self):
        """Return information about the device this sensor is part of."""
        return {
            "identifiers": {(DOMAIN, "battery_storage_sensors")},
            "name": "Battery Storage Automation",
            "manufacturer": "Zakery292",
        }

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        # Ensure a unique ID across different sensors
        return f"{unique_id_charge_plan_sensor}_{self._name}"

    async def async_update(self):
        # Check if the charging control is enabled
        _LOGGER.info("Starting async_update in BatteryChargePlanSensor")
        if not self.hass.data[DOMAIN].get("charging_control_enabled", False):
            _LOGGER.info("Charging control is not enabled. Charge plan is waiting.")
            self._state = "Waiting"
            self._attributes = {}
            return
        else:
            try:
                capacity_kwh = self.hass.data[DOMAIN].get("battery_capacity_kwh")
                soc_percentage = self.hass.data[DOMAIN].get("battery_charge_state")
                charge_rate_kwh = self.hass.data[DOMAIN].get("battery_charge_rate") / 1000
                rates_from_midnight = self.hass.data[DOMAIN]["rates_data"].get("rates_from_midnight", [])
                custom_soc_percentage = self.hass.data[DOMAIN].get("custom_soc_percentage")

                if not all([capacity_kwh, soc_percentage, charge_rate_kwh, rates_from_midnight]):
                    _LOGGER.error("One or more required data elements are missing or invalid.")
                    self._state = "Unavailable"
                    return

                # Default to 100% or use slider value if already set
                target_soc_percentage = 100 if custom_soc_percentage in [None, 0] else custom_soc_percentage
                _LOGGER.info(f"Target State of Charge Percentage: {target_soc_percentage}")
                # Calculate charge level and number of slots
                required_kwh = capacity_kwh * (target_soc_percentage - soc_percentage) / 100
                num_slots = math.ceil(max(required_kwh, 0) / (charge_rate_kwh / 2))
                _LOGGER.info(f"Required kWh: {required_kwh}, Number of slots: {num_slots}")


                sorted_rates = sorted(rates_from_midnight, key=lambda x: float(x['Cost'].rstrip('p')))
                cheapest_slots = sorted_rates[:num_slots]

                sorted_cheapest_slots = sorted(cheapest_slots, key=lambda x: x['Start Time'])
                slot_times = [slot['Start Time'] for slot in sorted_cheapest_slots]

                # Calculate total cost
                total_cost = sum(float(slot['Cost'].rstrip('p')) * (charge_rate_kwh / 2) for slot in sorted_cheapest_slots)

                # Update the slot_times in global domain data
                self.hass.data[DOMAIN]["slot_times"] = slot_times

                # Check for changes in custom_soc_percentage and update the plan if needed
                previous_soc_percentage = self.hass.data[DOMAIN].get("previous_soc_percentage")
                if custom_soc_percentage != previous_soc_percentage:
                    self.hass.data[DOMAIN]["previous_soc_percentage"] = custom_soc_percentage
                    _LOGGER.info("Slider value changed. Updating charge plan.")
                    self.hass.bus.async_fire("custom_charge_plan_updated_event", {"new_slot_times": slot_times})

                self._state = "Calculated"
                self._attributes = {
                    'required_slots': num_slots,
                    'total_cost': f"{total_cost:.2f}p",
                    'slot_times': slot_times
                }
                # Update the slot_times in global domain data
                self.hass.data[DOMAIN]["slot_times"] = slot_times
                self.async_write_ha_state()
            except Exception as e:
                _LOGGER.error(f"Error in BatteryChargePlanSensor update: {e}")
                self._state = "Error"

    async def async_periodic_update(self):
        while self.hass.data[DOMAIN].get("charging_control_enabled", False):
            await self.async_update()
            await asyncio.sleep(600)  # 30 minutes
            if self.time_reached_or_control_off():
                break

    def time_reached_or_control_off(self):
        # Implementation for time_reached_or_control_off method
        pass

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        return self._attributes
# charge sensor message

class ChargingStatusSensor(Entity):
    def __init__(self, name):
        self._name = name
        self._state = "Initializing"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name
    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return f"{unique_id_charging_status}_{self._name}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state
    @property
    def device_info(self):
        """Return information about the device this sensor is part of."""
        return {
            "identifiers": {(DOMAIN, "battery_storage_sensors")},
            "name": "Battery Storage Automation",
            "manufacturer": "Zakery292",
        }

    def update_state(self, new_state):
        """Update the state of the sensor."""
        self._state = new_state
        self.schedule_update_ha_state()



async def async_setup_entry(hass, entry, async_add_entities):
    """Setup sensor platform."""
    sensors = [
        OctopusEnergySensor("Afternoon Today", "afternoon_today"),
        OctopusEnergySensor("Afternoon Tomorrow", "afternoon_tomorrow"),
        OctopusEnergySensor("Rates From Midnight", "rates_from_midnight"),
        OctopusEnergySensor("All Rates", "all_rates"),
        OctopusEnergySensor("Rates Left", "rates_left"),
        OctopusEnergySensor("Current Import Rate", "current_import_rate"),
        BatteryStorageSensors("Battery Kwh", "battery_capacity_kwh"),
        BatteryChargePlanSensor("Battery Charge Plan"),
        ChargingStatusSensor("Charging Status")  # Add the charging status sensor
    ]
    hass.data[DOMAIN]["sensors"] = sensors
    hass.data[DOMAIN]["update_charge_plan"] = lambda: update_charge_plan(hass)

    async_add_entities(sensors, True)


    hass.data[DOMAIN]["charging_status_sensor"] = next((sensor for sensor in sensors if isinstance(sensor, ChargingStatusSensor)), None)

    charging_entity_start = entry.data.get("charging_entity_start")
    charging_entity_end = entry.data.get("charging_entity_end")
