import logging
from homeassistant.helpers.entity import Entity
from ..const import (
    DOMAIN,
    unique_id_battery_sensor,
)
from homeassistant.const import ENERGY_KILO_WATT_HOUR, DEVICE_CLASS_BATTERY


_LOGGER = logging.getLogger(__name__)


class BatteryStorageSensors(Entity):
    def __init__(self, name, sensor_type):
        self._name = name
        self._sensor_type = sensor_type
        self._state = None
        object_id = f"battery_storage_sensor{self._name.lower().replace(' ', '_')}"
        self.entity_id = f"sensor.{object_id}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} Sensor"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return DEVICE_CLASS_BATTERY

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return ENERGY_KILO_WATT_HOUR

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return f"{unique_id_battery_sensor}_{self._name}_{self._sensor_type}"

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

    async def async_update(self):
        try:
            # Using global variable for battery capacity in kWh
            battery_capacity_kwh = self.hass.data[DOMAIN]["battery_capacity_kwh"]
            _LOGGER.info("battery capacity kWh: %s", battery_capacity_kwh)
            if battery_capacity_kwh is None:
                self._state = "Unavailable"
            else:
                self._state = battery_capacity_kwh
        except Exception as e:
            _LOGGER.error(f"Error updating Battery Capacity: {e}")
            self._state = "Error"
