"""Define sensors for Battery Automation."""
import logging
from homeassistant.helpers.entity import Entity
from .octopus_api import get_octopus_energy_rates
from .const import get_api_key_and_account
import requests
from datetime import timedelta
from .const import DOMAIN

SCAN_INTERVAL = timedelta(minutes=30)  # Set the desired interval
_LOGGER = logging.getLogger(__name__)


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
            "manufacturer": "Octopus Energy",
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


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup sensor platform."""
    sensors = [
        OctopusEnergySensor("Afternoon Today", "afternoon_today"),
        OctopusEnergySensor("Afternoon Tomorrow", "afternoon_tomorrow"),
        OctopusEnergySensor("Rates From Midnight", "rates_from_midnight"),
        OctopusEnergySensor("All Rates", "all_rates"),
        OctopusEnergySensor("Rates Left", "pass"),
        OctopusEnergySensor("Current Import Rate", "current_import_rate"),
    ]

    async_add_entities(sensors, True)
