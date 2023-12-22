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

_LOGGER = logging.getLogger(__name__)


class BatteryChargePlanSensor(Entity):
    def __init__(self, name):
        self._name = name
        self._state = None
        self._attributes = {}
        self._last_soc = None

    async def async_added_to_hass(self):
        self.hass.bus.async_listen(
            "custom_slider_value_changed_event", self.handle_slider_change
        )
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

        _LOGGER.info("async_update called")
        _LOGGER.debug("".join(traceback.format_stack()))
        # Check if the charging control is enabled
        _LOGGER.info("Starting async_update in BatteryChargePlanSensor")
        soc_percentage = self.hass.data[DOMAIN].get("battery_charge_state")
        if not self.hass.data[DOMAIN].get("charging_control_enabled", False):
            _LOGGER.info("Charging control is not enabled. Charge plan is waiting.")
            self._state = "Waiting"
            self._attributes = {}
            return
        else:
            try:
                if self._last_soc is None or abs(soc_percentage - self._last_soc) >= 5 or now is not None:
                    self._last_soc = soc_percentage  # Update the last known SOC
                else:
                    _LOGGER.info("No significant SOC change, skipping update.")
                capacity_kwh = self.hass.data[DOMAIN].get("battery_capacity_kwh")
                soc_percentage = self.hass.data[DOMAIN].get("battery_charge_state")
                charge_rate_kwh = (
                    self.hass.data[DOMAIN].get("battery_charge_rate") / 1000
                )
                rates_from_midnight = self.hass.data[DOMAIN]["rates_data"].get(
                    "rates_left", []
                )
                custom_soc_percentage = self.hass.data[DOMAIN].get(
                    "custom_soc_percentage"
                )

                if not all(
                    [capacity_kwh, soc_percentage, charge_rate_kwh, rates_from_midnight]
                ):
                    _LOGGER.error(
                        "One or more required data elements are missing or invalid."
                    )
                    self._state = "Unavailable"
                    return

                # Default to 100% or use slider value if already set
                target_soc_percentage = (
                    100 if custom_soc_percentage in [None, 0] else custom_soc_percentage
                )
                _LOGGER.info(
                    f"Target State of Charge Percentage: {target_soc_percentage}"
                )
                # Calculate charge level and number of slots
                required_kwh = (
                    capacity_kwh * (target_soc_percentage - soc_percentage) / 100
                )
                num_slots = math.ceil(max(required_kwh, 0) / (charge_rate_kwh / 2))
                _LOGGER.info(
                    f"Required kWh: {required_kwh}, Number of slots: {num_slots}"
                )
                slot_times = []

                try:
                    now = datetime.now()

                    # Define the preferred time window and rate threshold
                    preferred_start_time = time(21, 0)  # 9 PM
                    preferred_end_time = time(8, 0)    # 8 AM
                    rate_threshold = 0.00  # £0.00 threshold

                    processed_rates = []
                    for rate in rates_from_midnight:
                        try:
                            rate_datetime = datetime.strptime(f"{rate['Date']} {rate['Start Time']}", "%d-%m-%Y %H:%M:%S")
                            rate_time = rate_datetime.time()
                            rate_cost = float(rate["Cost"].rstrip("p"))

                            if ((rate_time >= preferred_start_time or rate_time <= preferred_end_time) or rate_cost <= rate_threshold) and rate_datetime > now:
                                processed_rates.append({**rate, "cost": rate_cost, "datetime": rate_datetime})
                        except Exception as e:
                            _LOGGER.error(f"Error processing rate data: {e}")
                            # Optionally continue to the next rate or handle the error

                    # Sort processed rates by cost first, and then by datetime
                    sorted_processed_rates = sorted(processed_rates, key=lambda x: (x["cost"], x["datetime"]))

                    # Extract the cheapest slots based on the number of slots needed
                    cheapest_slots = sorted_processed_rates[:num_slots]

                    # Sort the cheapest slots by datetime to ensure correct ordering
                    cheapest_slots_sorted = sorted(cheapest_slots, key=lambda x: x["datetime"])

                    # Extract slot times from the sorted and filtered rates
                    slot_times = [slot["Start Time"] for slot in cheapest_slots_sorted]

                    # Calculate total cost
                    total_cost = sum(slot["cost"] * (charge_rate_kwh / 2) for slot in cheapest_slots_sorted)
                except Exception as e:
                    _LOGGER.error(f"Error in rates sorting battery charge plan: {e}")
                    self._state = "Error"

                # Update the slot_times in global domain data
                self.hass.data[DOMAIN]["slot_times"] = slot_times

                # Check for changes in custom_soc_percentage and update the plan if needed
                previous_soc_percentage = self.hass.data[DOMAIN].get(
                    "previous_soc_percentage"
                )
                if custom_soc_percentage != previous_soc_percentage:
                    self.hass.data[DOMAIN][
                        "previous_soc_percentage"
                    ] = custom_soc_percentage
                    _LOGGER.info("Slider value changed. Updating charge plan.")
                    self.hass.bus.async_fire(
                        "custom_charge_plan_updated_event",
                        {"new_slot_times": slot_times},
                    )

                self._state = "Calculated"
                self._attributes = {
                    "required_slots": num_slots,
                    "total_cost": f"{total_cost:.2f}p",
                    "slot_times": slot_times,
                }
                # Update the slot_times in global domain data
                self.hass.data[DOMAIN]["slot_times"] = slot_times
                self.async_write_ha_state()
            except Exception as e:
                _LOGGER.error(f"Error in BatteryChargePlanSensor update: {e}")
                self._state = "Error"

    async def async_periodic_update(self):
        while self.hass.data[DOMAIN].get("charging_control_enabled", False):
            await self.async_update(now=datetime.now())
            await asyncio.sleep(1800)  # Update every 30 minutes

            if self.time_reached_or_control_off():
                break

    def time_reached_or_control_off(self):
        # Implementation for time_reached_or_control_off method
        pass

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        return self._attributes
