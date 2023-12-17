"""Define sensors for Battery Automation."""
import logging
from homeassistant.helpers.entity import Entity
from .octopus_api import get_octopus_energy_rates, rates_data
from .const import get_api_key_and_account, DOMAIN
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta
import asyncio
import math

SCAN_INTERVAL = timedelta(seconds=120)  # Set the desired interval
_LOGGER = logging.getLogger(__name__)

#### Octopus Rates below #####


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
        return f"{self._name} Battery Sensors"
    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} Battery Sensors"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return f"{self._name}_{self._sensor_type}"

    @property
    def device_info(self):
        """Return information about the device this sensor is part of."""
        return {
            "identifiers": {(DOMAIN,)},
            "name": "Battery Storage Sensors",
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



###charge plan sensor ###
class BatteryChargePlanSensor(Entity):
    def __init__(self, name):
        self._name = name
        self._state = None
        self._attributes = {}

    @property
    def name(self):
        return f"{self._name} Charge Plan"

    @property
    def unique_id(self):
        return f"{self._name}_charge_plan"

    @property
    def state(self):
        return self._state



    async def async_update(self):
        try:
            capacity_kwh = self.hass.data[DOMAIN]["battery_capacity_kwh"]
            soc_percentage = self.hass.data[DOMAIN]["battery_charge_state"]
            charge_rate_kwh = self.hass.data[DOMAIN]["battery_charge_rate"] / 1000
            rates_from_midnight = self.hass.data[DOMAIN]["rates_data"].get("rates_from_midnight", [])

            if capacity_kwh is None or soc_percentage is None or charge_rate_kwh is None or not rates_from_midnight:
                self._state = "Unavailable"
                return

            required_kwh = capacity_kwh * (100 - soc_percentage) / 100
            _LOGGER.info("required kwh: %s", required_kwh)
            num_slots = math.ceil(required_kwh / (charge_rate_kwh / 2))  # Each slot is 30 minutes

            # Sort rates by cost and pick the required number of cheapest slots
            sorted_rates = sorted(rates_from_midnight, key=lambda x: float(x['Cost'].rstrip('p')))
            cheapest_slots = sorted_rates[:num_slots]

            # Sort the selected slots by their start time
            sorted_cheapest_slots = sorted(cheapest_slots, key=lambda x: x['Start Time'])

            # Calculate total cost and get the start times of sorted slots
            total_cost = sum(float(slot['Cost'].rstrip('p')) * (charge_rate_kwh / 2) for slot in sorted_cheapest_slots)
            slot_times = [slot['Start Time'] for slot in sorted_cheapest_slots]

            self._state = "Calculated"
            self._attributes = {
                'required_slots': num_slots,
                'total_cost': f"{total_cost:.2f}p",
                'slot_times': slot_times
            }
        except Exception as e:
            _LOGGER.error(f"Error in BatteryChargePlanSensor update: {e}")
            self._state = "Error"

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        return self._attributes

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        return self._attributes

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
        BatteryChargePlanSensor("Battery Charge Plan")
    ]
    async_add_entities(sensors, True)
