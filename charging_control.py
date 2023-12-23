# charge_plan.py
import asyncio
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
import logging
from .const import DOMAIN
from .sensors.battery_charge_plan_sensor import BatteryChargePlanSensor

_LOGGER = logging.getLogger(__name__)


class ChargingControl:
    def __init__(
        self, hass: HomeAssistant, charging_entity_start: str, charging_entity_end: str
    ):
        self.hass = hass
        self.charging_entity_start = charging_entity_start
        self.charging_entity_end = charging_entity_end
        self.slots = []
        self.current_slot_index = 0
        self._check_interval = 1800  # Time in seconds to check for charging time
        self.all_slots_processed = False
        self.waiting_for_plan = True
        self.loop_running = False  # Added to track if the control loop is running
        self.hass.bus.async_listen(
            "custom_charge_plan_updated_event", self.handle_charge_plan_update
        )
        self.last_charge_start = None
        self.last_charge_end = None

    async def handle_charge_plan_update(self, event):
        _LOGGER.info("Received updated charge plan event.")
        new_slots = event.data.get("new_slot_times", [])
        if new_slots != self.slots:
            self.slots = new_slots
            _LOGGER.info("Charge plan updated. Reprocessing slots.")
            await self.process_slots()

    async def reset_charging_control(self):
        """Reset the charging control to initial state."""
        self.all_slots_processed = True
        self.waiting_for_plan = True
        self.loop_running = False  # Ensure the loop stops running
        await self.reset_charging_times()  # Reset charging times to 00:00
        self.hass.data[DOMAIN]["charging_status_sensor"].update_state(
            "Waiting for charge plan"
        )

    async def update_charging_control_state(self, is_enabled: bool):
        """Update the state of the charging control."""
        self.hass.data[DOMAIN]["charging_control_enabled"] = is_enabled
        if is_enabled:
            _LOGGER.info("Charging control enabled. Starting control loop.")
            self.all_slots_processed = False  # Reset all_slots_processed
            self.waiting_for_plan = True  # Reset waiting_for_plan
            if not self.loop_running:
                self.loop_running = True
                self.hass.loop.create_task(self.control_loop())
        else:
            _LOGGER.info("Charging control disabled. Resetting control loop.")
            await self.reset_charging_control()

    async def control_loop(self):
        while self.loop_running:
            # First, check if the control is enabled
            if not self.hass.data[DOMAIN].get("charging_control_enabled", False):
                _LOGGER.info("Charging control is currently disabled.")
                break

            # Check if the plan is waiting for slots
            if self.waiting_for_plan:
                slots = self.hass.data[DOMAIN].get("slot_times", [])
                if not slots:
                    _LOGGER.info("No slots available. Waiting for new charge plan.")
                    self.hass.data[DOMAIN]["charging_status_sensor"].update_state(
                        "Waiting for new charge plan"
                    )
                    await asyncio.sleep(
                        self._check_interval
                    )  # Wait before checking again
                    continue
                else:
                    _LOGGER.info("Slots found. Proceeding with processing.")
                    self.waiting_for_plan = False

            # Process the slots
            await self.process_slots()

            # If all slots are processed, break the loop
            if self.all_slots_processed:
                _LOGGER.info("All slots have been processed.")
                break

            # Sleep for the defined interval before rechecking
            await asyncio.sleep(self._check_interval)

            if not self.all_slots_processed:
                await self.reset_charging_control()

    async def disable_charging_control(self):
        """Disable the charging control switch."""
        self.hass.data[DOMAIN]["charging_control_enabled"] = False
        _LOGGER.info("Charging control disabled after completing all slots.")



    ##### PROCESS SLOTS DATA #####

    async def process_slots(self):
        self.slots = self.hass.data[DOMAIN].get("slot_times", [])
        _LOGGER.info(f"Slot times: {self.slots}")

        charging_status_sensor = self.hass.data[DOMAIN].get("charging_status_sensor")

        if not self.slots:
            _LOGGER.info("No slots available.")
            if charging_status_sensor:
                charging_status_sensor.update_state(
                    "No valid charge plan available. Waiting for new charge plan."
                )
            self.all_slots_processed = True
            return

        now = datetime.now()
        _LOGGER.info(f"Current time: {now.strftime('%H:%M')}")

        slot_datetimes = [
            datetime.combine(now.date(), datetime.strptime(slot, "%H:%M:%S").time())
            for slot in self.slots
        ]
        # Adjust for slots after midnight
        slot_datetimes = [
            slot_datetime + timedelta(days=1) if slot_datetime < now else slot_datetime
            for slot_datetime in slot_datetimes
        ]

        # Check for consecutive slots and combine them
        combined_slots = []
        start_slot = slot_datetimes[0]
        end_slot = start_slot

        for slot_datetime in slot_datetimes[1:]:
            if slot_datetime == end_slot + timedelta(minutes=30):
                end_slot = slot_datetime
            else:
                combined_slots.append((start_slot, end_slot + timedelta(minutes=30)))
                start_slot = slot_datetime
                end_slot = slot_datetime

        combined_slots.append((start_slot, end_slot + timedelta(minutes=30)))

        # Set the first combined slot immediately
        first_start, first_end = combined_slots[0]
        if first_start != self.last_charge_start or first_end != self.last_charge_end:
            self.last_charge_start = first_start
            self.last_charge_end = first_end
            await self.set_charging_times(
                first_start.strftime("%H:%M"), first_end.strftime("%H:%M")
            )

        # Update charging status sensor for the first combined slot
        if charging_status_sensor:
            next_slot_info = (
                f"Next slot: {combined_slots[1][0].strftime('%H:%M')}"
                if len(combined_slots) > 1
                else "No more slots."
            )
            charging_status_sensor.update_state(
                f"Charging from {first_start.strftime('%H:%M')} to {first_end.strftime('%H:%M')}. {next_slot_info}"
            )

        # Handle subsequent combined slots
        for i, (start_slot, end_slot) in enumerate(combined_slots):
            # Calculate remaining time until start of the slot
            remaining_time = (start_slot - now).total_seconds()

            while remaining_time > 0:
                # Calculate hours and minutes for countdown message
                hours, remainder = divmod(remaining_time, 3600)
                minutes, _ = divmod(remainder, 60)

                # Update charging status sensor with countdown
                countdown_message = f"Next slot starts in {int(hours)}h {int(minutes)}m. At {first_start.strftime('%H:%M')} "
                if charging_status_sensor:
                    charging_status_sensor.update_state(countdown_message)

                # Wait for 1 minute or until the slot start time
                await asyncio.sleep(min(60, remaining_time))
                now = datetime.now()
                remaining_time = (start_slot - now).total_seconds()

            # Set charging times for the current slot
            await self.set_charging_times(
                start_slot.strftime("%H:%M"), end_slot.strftime("%H:%M")
            )

            # Update status for the current slot
            if charging_status_sensor:
                slot_message = f"Charging from {start_slot.strftime('%H:%M')} to {end_slot.strftime('%H:%M')}."
                charging_status_sensor.update_state(slot_message)

            # Update for next combined slot, if exists
            if i + 1 < len(combined_slots):
                next_start, _ = combined_slots[i + 1]
                if charging_status_sensor:
                    charging_status_sensor.update_state(
                        f"Charging slot from {start_slot.strftime('%H:%M')} to {end_slot.strftime('%H:%M')} active. Next slot: {next_start.strftime('%H:%M')}"
                    )
            else:
                self.all_slots_processed = True
                if charging_status_sensor:
                    charging_status_sensor.update_state(
                        f"All charging slots for today processed. The last slot ends at {end_slot.strftime('%H;%M')}."
                    )
                break

    async def set_charging_times(self, start_time, end_time):
        start_time_obj = datetime.strptime(start_time, "%H:%M").time()
        end_time_obj = datetime.strptime(end_time, "%H:%M").time()

        await self.update_time_entity(self.charging_entity_start, start_time_obj)
        await self.update_time_entity(self.charging_entity_end, end_time_obj)
        _LOGGER.info(
            f"Set charging start time to: {start_time} and end time to: {end_time}"
        )

    async def update_time_entity(self, entity_id, time_value):
        entity = self.hass.states.get(entity_id)
        if entity is None:
            _LOGGER.error(f"Entity {entity_id} not found")
            return

        # Get the actual entity object from Home Assistant
        entity_object = self.hass.data["entity_components"]["time"].get_entity(
            entity_id
        )
        if entity_object is None:
            _LOGGER.error(f"Entity object for {entity_id} not found")
            return

        try:
            # Call the set_value method of LuxTimeTimeEntity
            if asyncio.iscoroutinefunction(entity_object.set_value):
                await entity_object.set_value(time_value)
            else:
                entity_object.set_value(time_value)
            _LOGGER.info(f"Updated {entity_id} to {time_value}")
        except Exception as e:
            _LOGGER.error(f"Failed to update {entity_id} to {time_value}: {e}")

    async def reset_charging_times(self):
        zero_time = datetime.strptime("00:00", "%H:%M").time()
        await self.update_time_entity(self.charging_entity_start, zero_time)
        await self.update_time_entity(self.charging_entity_end, zero_time)
        _LOGGER.info("Charging times reset to 00:00")
