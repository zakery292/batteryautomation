from homeassistant.helpers.entity import Entity
from datetime import timedelta
from ..battery_soc_calcs import calculate_average_decline
from ..const import DOMAIN, unique_id_average_battery_usage


class AverageBatteryUsageSensor(Entity):
    def __init__(self, hass, name, period):
        self._hass = hass
        self._name = name
        self._state = None
        self._period = period

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        # Ensure a unique ID across different sensors
        return f"{unique_id_average_battery_usage}_{self._name}"

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

    async def async_update(self):
        try:
            average_decline = await self._hass.async_add_executor_job(
                calculate_average_decline, self._hass, self._period
            )
            self._state = (
                average_decline if average_decline is not None else "Not enough data"
            )
        except Exception as e:
            self._state = "Error"
