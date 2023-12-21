# switch.py
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN, unique_id_charging_control_switch
import logging
import asyncio
_LOGGER = logging.getLogger(__name__)

class ChargingControlSwitchEntity(SwitchEntity):
    """A virtual switch for enabling or disabling charging control."""

    def __init__(self, hass: HomeAssistant, name: str, update_callback):
        super().__init__()
        self._hass = hass
        self._name = name
        self._state = False
        self._update_callback = update_callback

    @property
    def name(self):
        """Return the display name of this switch."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return f"{unique_id_charging_control_switch}_{self._name}"

    @property
    def device_info(self):
        """Return information about the device this sensor is part of."""
        return {
            "identifiers": {(DOMAIN, "battery_storage_sensors")},
            "name": "Battery Storage Automation",
            "manufacturer": "Zakery292",
        }
    @property
    def is_on(self):
        """Return True if the switch is on."""
        return self._state

    async def async_turn_on(self, **kwargs):
        self._state = True
        self.async_write_ha_state()

        self.hass.data[DOMAIN]["charging_control_enabled"] = True

        # Call the update_charge_plan function
        update_charge_plan = self.hass.data[DOMAIN].get("update_charge_plan")
        if update_charge_plan:
            await update_charge_plan()
        charging_control = self.hass.data[DOMAIN].get("charging_control")
        if charging_control:
            await charging_control.update_charging_control_state(True)

        # Turn on the ac_charge switch based on the provided entity_id
        ac_charge_entity_id = self._hass.data[DOMAIN].get("ac_charge_entity_id")
        if ac_charge_entity_id:
            try:
                await self.hass.services.async_call(
                    "switch",
                    "turn_on",
                    {"entity_id": ac_charge_entity_id}
                )
                _LOGGER.info(f"Turning on AC charge switch: {ac_charge_entity_id}")
            except Exception as e:
                _LOGGER.error(f"Error turning on AC charge switch: {e}")

    async def async_turn_off(self, **kwargs):
        self._state = False
        self.async_write_ha_state()

        # Update charging control state
        self.hass.data[DOMAIN]["charging_control_enabled"] = False

        charging_control = self.hass.data[DOMAIN].get("charging_control")
        if charging_control:
            await charging_control.reset_charging_control()

        # Turn off the ac_charge switch based on the provided entity_id
        ac_charge_entity_id = self._hass.data[DOMAIN].get("ac_charge_entity_id")
        if ac_charge_entity_id:
            try:
                await self.hass.services.async_call(
                    "switch",
                    "turn_off",
                    {"entity_id": ac_charge_entity_id}
                )
                _LOGGER.info(f"Turning off AC charge switch: {ac_charge_entity_id}")
            except Exception as e:
                _LOGGER.error(f"Error turning off AC charge switch: {e}")

    @property
    def should_poll(self):
        """Indicate that this entity should not be polled."""
        return False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Setup switch platform."""
    # Retrieve the update_charge_plan function from global data
    update_charge_plan = hass.data[DOMAIN].get("update_charge_plan")
    switch_entity = ChargingControlSwitchEntity(hass, "Charging Control Switch", update_charge_plan)
    async_add_entities([switch_entity], True)

