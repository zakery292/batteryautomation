import logging
from homeassistant.helpers.entity import Entity
from ..const import (
    DOMAIN,
    unique_id_charge_plan_sensor,
)
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta, datetime, time
import asyncio
import math
import traceback
from datetime import datetime, time, timedelta
from ..charge_plan_creator import create_charge_plan

_LOGGER = logging.getLogger(__name__)


class BatteryChargePlanSensor(Entity):
    def __init__(self, name):
        self._name = name
        self._state = None
        self._attributes = {}
        self._last_soc = None
        object_id = f"battery_charge_plan_sensor{self._name.lower().replace(' ', '_')}"
        self.entity_id = f"sensor.{object_id}"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        # Listener for custom slider value change event
        self.hass.bus.async_listen(
            "custom_slider_value_changed_event", self.handle_slider_change
        )

        # Listener for battery charge plan update event
        self.hass.bus.async_listen(
            "battery_charge_plan_update", self.handle_charge_plan_update
        )

    async def handle_charge_plan_update(self, event):
        _LOGGER.info("Received request to update charge plan.")
        await self.async_update()

    async def handle_slider_change(self, event):
        _LOGGER.info("Detected slider change in BatteryChargePlanSensor.")
        await self.async_update()

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        return f"{self._name} Charge Plan"

    @property
    def state(self):
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return "mdi:battery-charging"

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
        return f"{unique_id_charge_plan_sensor}_{self._name}"

    async def async_update(self, now=None):
        if self.hass is None:
            _LOGGER.error("Home Assistant core is not fully set up yet.")
            return

        charging_control_enabled = self.hass.data[DOMAIN].get(
            "charging_control_enabled", False
        )
        if not charging_control_enabled:
            self._state = "No Plan"
            self._attributes = {}
            return

        try:
            rates_data = self.hass.data[DOMAIN].get("rates_data", {})
            capacity_kwh = self.hass.data[DOMAIN].get("battery_capacity_kwh")
            soc_percentage = self.hass.data[DOMAIN].get("battery_charge_state")
            charge_rate_kwh = self.hass.data[DOMAIN].get("battery_charge_rate") / 1000
            rates_from_midnight = rates_data.get("rates_from_midnight", [])
            evening_today = rates_data.get("evening_today", [])
            afternoon_today = rates_data.get("afternoon_today", [])

            custom_soc_percentage = self.hass.data[DOMAIN].get(
                "custom_soc_percentage", 100
            )  # Default to 100 if not set

            num_slots, total_cost, slot_times = create_charge_plan(
                capacity_kwh,
                soc_percentage,
                charge_rate_kwh,
                afternoon_today,
                evening_today,
                rates_from_midnight,
                custom_soc_percentage,
            )

            if slot_times == "":
                self._state = "Waiting for next period"
                self._attributes = {
                    "required_slots": num_slots,
                    "slot_times": slot_times,
                }
            else:
                self._state = "Calculated"
                self._attributes = {
                    "required_slots": num_slots,
                    "total_cost": f"{total_cost:.2f}p",
                    "slot_times": slot_times,
                }

            # New code to check if slot_times have changed and fire an event
            if self.hass.data[DOMAIN].get("slot_times") != slot_times:
                self.hass.data[DOMAIN]["slot_times"] = slot_times
                self.hass.bus.async_fire(
                    "custom_charge_plan_updated_event", {"new_slot_times": slot_times}
                )
                _LOGGER.info(
                    "Fired custom_charge_plan_updated_event with new slot times"
                )

            # Update Home Assistant state
            self.async_write_ha_state()

        except Exception as e:
            _LOGGER.error(f"Error in BatteryChargePlanSensor update: {e}")
            self._state = "Error"

    def time_reached_or_control_off(self):
        # Implementation for time_reached_or_control_off method
        pass

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        return self._attributes
