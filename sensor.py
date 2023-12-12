"""Define sensors for Battery Automation."""
import logging
from homeassistant.helpers.entity import Entity
from .octopus_api import get_octopus_energy_rates
from .const import get_api_key_and_account

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

    async def async_update(self):
        """Fetch new state data for the sensor."""
        try:
            rates = await get_octopus_energy_rates(
                self._api_key, self._account_id, self._sensor_type
            )
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
    ]

    async_add_entities(sensors, True)
