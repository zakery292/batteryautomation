# sensor.py
from homeassistant.helpers.entity import Entity
from .octopus_api import get_octopus_energy_rates

class OctopusEnergySensor(Entity):
    def __init__(self, api_key, account_id, name, sensor_type):
        self._api_key = api_key
        self._account_id = account_id
        self._name = name
        self._sensor_type = sensor_type
        self._state = None

    @property
    def name(self):
        return f"{self._name} Octopus Energy"

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return "your unit of measurement"

    def update_data(self, now):
        try:
            rates = get_octopus_energy_rates(self._api_key, self._account_id, self._sensor_type)

            # Process rates as needed based on your data structure
            # For example, update self._state with the relevant information
            if self._sensor_type == "rates_from_midnight":
                self._state = len(rates)  # Update with your logic
            elif self._sensor_type == "afternoon_today":
                self._state = sum(item["value"] for item in rates)  # Update with your logic
            elif self._sensor_type == "afternoon_tomorrow":
                self._state = max(item["value"] for item in rates)  # Update with your logic
            else:
                _LOGGER.warning("Invalid rate type specified.")

        except Exception as e:
            _LOGGER.error(f"Error updating Octopus Energy data: {e}")
