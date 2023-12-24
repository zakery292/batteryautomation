from homeassistant.helpers.entity import Entity
from datetime import timedelta
from ..battery_predictions import predict_peak_hours_soc
from ..const import DOMAIN, unique_id_peak_hours
from homeassistant.const import PERCENTAGE, DEVICE_CLASS_BATTERY
import logging
from datetime import datetime

_LOGGER = logging.getLogger(__name__)


class PeakHours(Entity):
    def __init__(self, hass, name, period, mode):
        self._hass = hass
        self._name = name
        self._state = None
        self._period = period
        self._peak_hours_predictions = None

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        # Ensure a unique ID across different sensors
        return f"{unique_id_peak_hours}_{self._name}"

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return DEVICE_CLASS_BATTERY

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return PERCENTAGE

    @property
    def state(self):
        return self._state

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
        return False

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {"peak_hours_predictions": self._peak_hours_predictions}

    async def async_update(self):
        try:
            # retrieve dynamic lookback period
            # Only fetch and process predictions, don't update lookback period here
            lookback_days = self._hass.data[DOMAIN].get("lookback_period", 1)
            _LOGGER.info(f"Loopback update: {lookback_days}")
            lookback_days = timedelta(lookback_days)

            # Fetch and store predictions
            self._peak_hours_predictions = await self._hass.async_add_executor_job(
                predict_peak_hours_soc, self._hass, lookback_days
            )

            # Store the peak hours predictions in hass.data[DOMAIN]
            self._hass.data[DOMAIN][
                "peak_hour_predictions"
            ] = self._peak_hours_predictions

            # Find the nearest upcoming peak hour prediction
            current_time = datetime.now()
            nearest_prediction_time = None
            nearest_prediction_value = None
            for peak_hour, prediction in self._peak_hours_predictions.items():
                peak_hour_time = datetime.strptime(
                    peak_hour, "%H:%M"
                ).time()  # Corrected format
                if current_time.time() <= peak_hour_time and prediction is not None:
                    nearest_prediction_time = peak_hour
                    nearest_prediction_value = prediction
                    _LOGGER.info(
                        f"Peak updated prediction Value: {nearest_prediction_value}"
                    )
                    break

            # Update the state with the nearest prediction and time
            if nearest_prediction_time and nearest_prediction_value is not None:
                self._state = f"{nearest_prediction_value}"
            else:
                self._state = "No prediction available"
        except Exception as e:
            _LOGGER.error(f"Error updating sensor: {e}")
            self._state = "Error"
