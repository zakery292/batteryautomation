# octopus_energy_sensor.py
import logging
from homeassistant.helpers.entity import Entity
from ..const import (
    get_api_key_and_account,
    DOMAIN,
)
from datetime import datetime, timedelta
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_interval

_LOGGER = logging.getLogger(__name__)


class OctopusEnergySensor(Entity):
    def __init__(self, name, rate_type):
        self._name = name
        self._rate_type = rate_type
        self._state = None
        self._attributes = {}
        self._api_key, self._account_id = get_api_key_and_account()
        self._last_sensor_update = None

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

    async def async_refresh(self):
        """Refresh the sensor data."""
        _LOGGER.info(f"Refreshing data for sensor {self._name}")
        # Fetch the new rates data and update sensor state
        await self.async_update()
        # Ensure Home Assistant knows the state might have changed
        self.async_write_ha_state()

    async def async_update(self):
        """Fetch new data and update state."""
        current = datetime.now()
        if (
            self._last_sensor_update is None
            or current - self._last_sensor_update >= timedelta(minutes=30)
        ):
            _LOGGER.info(f"Failsafe update triggered for {self._name}")

        _LOGGER.info(f"Attempting to update Octopus Energy data for {self._name}")

        try:
            rates = self.hass.data[DOMAIN]["rates_data"].get(self._rate_type, [])
            if rates:
                new_state = (
                    rates[0].get("Cost")
                    if self._rate_type == "current_import_rate"
                    else "Data Available"
                )
                _LOGGER.debug(f"New state for {self._name}: {new_state}")
                _LOGGER.debug(f"New attributes for {self._name}: {rates}")

                if new_state != self._state or rates != self._attributes.get("rates"):
                    _LOGGER.info(
                        f"State or attributes have changed for {self._name}, updating..."
                    )
                    self._state = new_state
                    self._attributes["rates"] = rates
                    self._last_sensor_update = datetime.now()
                    self.async_write_ha_state()
                else:
                    _LOGGER.info(
                        f"No change in state or attributes for {self._name}, no update needed."
                    )
            else:
                _LOGGER.warning(f"No rate data found for {self._name}.")
                if self._state != "No Data":
                    self._state = "No Data"
                    self._attributes = {}
                    self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error(f"Error updating Octopus Energy data for {self._name}: {e}")
