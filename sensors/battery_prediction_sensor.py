from homeassistant.helpers.entity import Entity
from ..battery_predictions import predict_future_state
from datetime import timedelta
from ..const import DOMAIN, unique_id_battery_predicitons
import logging

_LOGGER = logging.getLogger(__name__)

class BatteryPredictionSensor(Entity):
    def __init__(self, hass, name, prediction_horizon):
        self._hass = hass
        self._name = name
        self._state = None
        self._prediction_horizon = prediction_horizon

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        # Ensure a unique ID across different sensors
        return f"{unique_id_battery_predicitons}_{self._name}"

    @property
    def state(self):
        return self._state
    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def device_info(self):
        """Return information about the device this sensor is part of."""
        return {
            "identifiers": {(DOMAIN, "battery_storage_sensors")},
            "name": "Battery Storage Automation",
            "manufacturer": "Zakery292",
        }

    async def async_update(self):
        lookback_period = timedelta(days=1)  # Adjust as needed
        self._state = await self._hass.async_add_executor_job(
            predict_future_state, self._hass, self._prediction_horizon, lookback_period
        )
        _LOGGER.info(f'Battery Predicitons 1/6 updated')
