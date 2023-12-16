"""Define sensors for Battery Automation."""
import logging
from homeassistant.helpers.entity import Entity
from .octopus_api import get_octopus_energy_rates
from .const import get_api_key_and_account
import requests
from datetime import timedelta
from .const import DOMAIN
from homeassistant.helpers.event import async_track_time_interval


SCAN_INTERVAL = timedelta(seconds=120)  # Set the desired interval
_LOGGER = logging.getLogger(__name__)

#### Octopus Rates below #####


class OctopusEnergySensor(Entity):
    def __init__(self, name, sensor_type):
        # Initialize the sensor
        self._name = name
        self._sensor_type = sensor_type
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
        return f"{self._account_id}_{self._sensor_type}"

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
            rates = await get_octopus_energy_rates(
                self._api_key, self._account_id, self._sensor_type
            )
            _LOGGER.info("sensor py logger rates: %s", rates)
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
    def __init__(self, name, sensor_type, battery_capacity_entity_id):
        self._name = name
        self._sensor_type = sensor_type
        self._battery_capacity_entity_id = battery_capacity_entity_id # battery capacity
        self._state = None
        self._update_interval = timedelta(minutes=2)  # Set update interval to 2 minutes
        self._unavailable_counter = 0  # Counter to track unavailable updates

    async def async_added_to_hass(self):
        """When entity is added to Home Assistant."""
        # Schedule regular updates
        self._update_unsub = async_track_time_interval(
            self.hass, self.async_update, self._update_interval
        )
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
        """Fetch new state data for the sensor."""
        try:
            battery_capacity_state = self.hass.states.get(self._battery_capacity_entity_id)
            # ... existing update logic ...

            # Reset counter if data is available
            if self._state not in [None, 'No Data', 'Error']:
                self._unavailable_counter = 0
            else:
                # Increment counter if data is unavailable
                self._unavailable_counter += 1
                if self._unavailable_counter >= 15:  # e.g., 30 minutes elapsed
                    # Perform some fallback or recheck logic if needed
                    pass

        except Exception as e:
            _LOGGER.error(f"Error updating Battery Capacity: {e}")
            self._state = "Error"

    def __del__(self):
        """When entity is removed from Home Assistant."""
        if self._update_unsub:
            self._update_unsub()




###charge plan sensor ###
class BatteryChargePlanSensor(Entity):
    def __init__(self, name, sensor_battery_capacity_kwh, battery_charge_entity_id, battery_charge_rate_entity_id, sensor_octopus_rates):
        self._name = name
        self._sensor_battery_capacity_kwh = sensor_battery_capacity_kwh
        self._battery_charge_entity_id = battery_charge_entity_id
        self._battery_charge_rate_entity_id = battery_charge_rate_entity_id
        self._sensor_octopus_rates = sensor_octopus_rates
        self._state = None
        self._attributes = {}

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    async def async_update(self):
        """Fetch new state data for the sensor."""
        try:
            # Fetch data from other sensors
            capacity_kwh = float(self.hass.states.get(self._sensor_battery_capacity_kwh).state)
            soc_percentage = float(self.hass.states.get(self._sensor_battery_soc).state)
            charge_rate_kwh = float(self.hass.states.get(self._sensor_charge_rate).state)
            rates = self.hass.states.get(self._sensor_octopus_rates).attributes['rates']

            # Calculate required kWh to charge
            required_kwh = capacity_kwh * (100 - soc_percentage) / 100

            # Calculate the number of slots and total cost
            slots, total_cost = self.calculate_charge_slots(required_kwh, charge_rate_kwh, rates)

            # Update sensor state and attributes
            self._state = len(slots)
            self._attributes['slots'] = slots
            self._attributes['total_cost'] = total_cost

        except Exception as e:
            _LOGGER.error(f"Error updating Battery Charge Plan: {e}")
            self._state = "Error"

    def calculate_charge_slots(self, required_kwh, charge_rate_kwh, rates):
        slots = []
        total_cost = 0
        remaining_kwh = required_kwh

        for rate in rates:
            if remaining_kwh <= 0:
                break

            slot_kwh = min(charge_rate_kwh, remaining_kwh)
            slot_cost = slot_kwh * rate['Cost']
            slots.append({
                'time': rate['Start Time'],
                'kwh': slot_kwh,
                'cost': slot_cost
            })

            total_cost += slot_cost
            remaining_kwh -= slot_kwh

        return slots, total_cost


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup sensor platform."""
    battery_capacity_entity_id = entry.data.get("battery_capacity")
    battery_charge_rate = entry.data.get("battery_charge_rate")
    sensors = [
        OctopusEnergySensor("Afternoon Today", "afternoon_today"),
        OctopusEnergySensor("Afternoon Tomorrow", "afternoon_tomorrow"),
        OctopusEnergySensor("Rates From Midnight", "rates_from_midnight"),
        OctopusEnergySensor("All Rates", "all_rates"),
        OctopusEnergySensor("Rates Left", "rates_left"),
        OctopusEnergySensor("Current Import Rate", "current_import_rate"),
        BatteryStorageSensors(
            "Battery Kwh", "battery_capacity_kwh", battery_capacity_entity_id
        ),
        BatteryChargePlanSensor("Battery Charge Plan", "battery_charge_plan", battery_charge_rate)
    ]

    async_add_entities(sensors, True)