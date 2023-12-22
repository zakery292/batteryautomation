import logging
from homeassistant.helpers.entity import Entity
from ..octopus_api import get_octopus_energy_rates, rates_data
from ..const import (
    get_api_key_and_account,
    DOMAIN,
)
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta, datetime, time
import asyncio
import math
_LOGGER = logging.getLogger(__name__)


class OctopusEnergySensor(Entity):
    def __init__(self, name, rate_type):
        self._name = name
        self._rate_type = rate_type
        self._state = None
        self._attributes = {}
        self._api_key, self._account_id = get_api_key_and_account()
        self._last_sensor_update = datetime.min
    #@property
    #def update_interval(self):
       # """Return the polling interval for the sensor."""
       # return SCAN_INTERVAL

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
        return False

    async def async_update(self):
        _LOGGER.info(f"Updating Octopus Energy data for {self._name}")

        # Call update_local_rates_data to update rates before async_updat
        try:
            rates = self.hass.data[DOMAIN]["rates_data"].get(self._rate_type, [])
            if rates:
                self._state = "Data Available"
                self._attributes["rates"] = rates
                if self._rate_type == "current_import_rate":
                    current_rate = rates[0].get("Cost")
                    if current_rate is not None:
                        self._state = current_rate
            else:
                self._state = "No Data"
                self._attributes = {}
        except Exception as e:
            _LOGGER.error(f"Error updating Octopus Energy data: {e}")
            self._state = "Error"
            self._attributes = {}
