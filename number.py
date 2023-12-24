from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN, unique_id_custom_soc_percentage, unique_id_lookback
import logging
from homeassistant.const import DEVICE_CLASS_BATTERY, PERCENTAGE

_LOGGER = logging.getLogger(__name__)


class CustomSocPercentage(NumberEntity):
    """A number entity to set the required State of Charge percentage."""

    def __init__(self, hass: HomeAssistant, name: str):
        self._hass = hass
        self._name = name
        self._state = hass.data[DOMAIN].get("custom_soc_percentage")
        object_id = f"custom_soc_percentage{self._name.lower().replace(' ', '_')}"
        self.entity_id = f"sensor.{object_id}"

    @property
    def name(self):
        """Return the display name of this entity."""
        return self._name

    @property
    def device_class(self):
        """Return the display name of this entity."""
        return DEVICE_CLASS_BATTERY

    @property
    def unit_of_measurement(self):
        """Return the display name of this entity."""
        return PERCENTAGE

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return f"{unique_id_custom_soc_percentage}_{self._name}"

    @property
    def min_value(self):
        """Return the minimum value."""
        return 1

    @property
    def max_value(self):
        """Return the maximum value."""
        return 100

    @property
    def step(self):
        """Return the increment/decrement step."""
        return 1

    @property
    def value(self):
        """Return the current value."""
        return self._state

    async def async_set_native_value(self, value: float):
        """Set the native value of the entity."""
        # Check if the value is actually changing
        if self._state != value:
            self._state = value
            self._hass.data[DOMAIN]["custom_soc_percentage"] = value
            self.async_write_ha_state()

            # Fire the event to indicate the slider value has changed
            self._hass.bus.async_fire(
                "custom_slider_value_changed_event", {"new_value": value}
            )
            _LOGGER.info(f"Slider value changed to {value}.")

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
        """Indicate that this entity should not be polled."""
        return False


class LookbackNumberEntity(NumberEntity):
    def __init__(self, hass: HomeAssistant, name: str):
        self._hass = hass
        self._name = name
        self._attr_min_value = 1
        self._attr_max_value = 7
        self._attr_step = 1
        self._attr_unique_id = unique_id_lookback
        self._attr_value = 1
        self._attr_mode = NumberMode.BOX
        object_id = f"lookback_entry{self._name.lower().replace(' ', '_')}"
        self.entity_id = f"sensor.{object_id}"

    @property
    def name(self):
        """Return the display name of this entity."""
        return self._name

    @property
    def max_value(self):
        """Return Max value"""
        return 7

    @property
    def device_info(self):
        """Return information about the device this sensor is part of."""
        return {
            "identifiers": {(DOMAIN, "battery_storage_sensors")},
            "name": "Battery Storage Automation",
            "manufacturer": "Zakery292",
        }

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        # Ensure a unique ID across different sensors
        return f"{unique_id_lookback}_{self._name}"

    @property
    def value(self):
        """Return the value of the number entity."""
        return self._attr_value

    def set_native_value(self, value):
        """Set the value of the lookback period."""
        if self._attr_value != value:
            self._attr_value = value
            self.hass.data[DOMAIN]["lookback_period"] = value
            self.async_write_ha_state()

            # Fire a custom event
            self.hass.bus.async_fire("lookback_period_changed", {"value": value})


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Setup number platform."""
    # Add the CustomSocPercentage to Home Assistant
    async_add_entities(
        [
            CustomSocPercentage(hass, "State Of Charge Required"),
            LookbackNumberEntity(hass, " Lookback Period For Battery Predictions"),
        ],
        True,
    )
