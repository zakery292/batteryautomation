from homeassistant.helpers.entity import Entity
from datetime import timedelta
from ..battery_soc_calcs import (
    calculate_average_change,
    calculate_total_percentage_change,
)
from ..battery_predictions import predict_peak_hours_soc
from ..const import DOMAIN, unique_id_average_battery_usage
from homeassistant.const import PERCENTAGE, DEVICE_CLASS_BATTERY
import logging

_LOGGER = logging.getLogger(__name__)


class AverageBatteryUsageSensor(Entity):
    def __init__(self, hass, name, period, mode):
        self._hass = hass
        self._name = name
        self._state = None
        self._period = period
        self._mode = mode
        self._peak_hours_predictions = None
        object_id = (
            f"average_battery_useage_sensor{self._name.lower().replace(' ', '_')}"
        )
        self.entity_id = f"sensor.{object_id}"

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        # Ensure a unique ID across different sensors
        return f"{unique_id_average_battery_usage}_{self._name}"

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
    def extra_state_attributes(self):
        """Return the state attributes."""
        # Include peak hours predictions only if mode is set for it
        if self._mode == "peak_hours":
            return {"peak_hours_predictions": self._peak_hours_predictions}
        return {}

    async def async_update(self):
        try:
            if self._mode in ["usage", "charge"]:
                # For average change calculations
                average_charge, average_usage = await self._hass.async_add_executor_job(
                    calculate_average_change, self._hass, self._period
                )
                if self._mode == "usage":
                    self._state = (
                        average_usage
                        if average_usage is not None
                        else "Not enough data"
                    )
                elif self._mode == "charge":
                    self._state = (
                        average_charge
                        if average_charge is not None
                        else "Not enough data"
                    )
            elif self._mode == "total":
                # For total percentage change calculations
                total_charge, total_discharge = await self._hass.async_add_executor_job(
                    calculate_total_percentage_change,
                    self._hass,
                    self._period,
                    self._hass.data[DOMAIN]["battery_capacity_kwh"],
                )
                self._state = (
                    total_discharge
                    if total_discharge is not None
                    else "Not enough data"
                )

            # Handling for peak hours predictions
            if self._mode == "peak_hours":
                self._peak_hours_predictions = await self._hass.async_add_executor_job(
                    predict_peak_hours_soc, self._hass, self._period
                )
                # Update state or additional attributes as needed
        except Exception as e:
            _LOGGER.error(f"Error updating sensor: {e}")
            self._state = "Error"
