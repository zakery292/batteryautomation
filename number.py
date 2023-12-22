from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN, unique_id_custom_soc_percentage
import logging

_LOGGER = logging.getLogger(__name__)

class CustomSocPercentage(NumberEntity):
    """A number entity to set the required State of Charge percentage."""

    def __init__(self, hass: HomeAssistant, name: str):
        self._hass = hass
        self._name = name
        self._state = hass.data[DOMAIN].get("custom_soc_percentage")

    @property
    def name(self):
        """Return the display name of this entity."""
        return self._name

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
            self._hass.bus.async_fire("custom_slider_value_changed_event", {"new_value": value})
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

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Setup number platform."""
    # Add the CustomSocPercentage to Home Assistant
    async_add_entities(
        [CustomSocPercentage(hass, "State Of Charge Required")],
        True
    )
