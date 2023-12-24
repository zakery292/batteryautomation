import logging
from homeassistant.helpers.entity import Entity
from .const import DOMAIN
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta, datetime, time
import asyncio
import math
import traceback
from datetime import datetime, time, timedelta

_LOGGER = logging.getLogger(__name__)


def calculate_required_kwh(capacity_kwh, soc_percentage, custom_soc_percentage):
    # Check the slider's value and choose the target SOC accordingly
    target_soc_percentage = (
        100 if custom_soc_percentage in [None, 0] else custom_soc_percentage
    )

    # Calculate the required kWh based on the target SOC
    required_kwh = capacity_kwh * (target_soc_percentage - soc_percentage) / 100
    return required_kwh


def create_afternoon_charge_plan(afternoon_today, num_slots, charge_rate_kwh):
    try:
        _LOGGER.info("Creating afternoon charge plan")
        current_time = datetime.now().time()

        # Convert 'Cost' from string to float and remove the 'p' (assuming all costs end with 'p')
        for rate in afternoon_today:
            if isinstance(rate["Cost"], str):
                rate["Cost"] = float(rate["Cost"].rstrip("p"))

        # Filter rates for the afternoon period and below the price threshold
        afternoon_rates_filtered = [
            rate for rate in afternoon_today if rate["Cost"] < 10.00
        ]
        _LOGGER.debug(f"Afternoon rates after filtering: {afternoon_rates_filtered}")

        # Sort rates by cost, then by datetime
        sorted_afternoon_rates = sorted(
            afternoon_rates_filtered, key=lambda x: (x["Cost"], x["Start Time"])
        )
        _LOGGER.debug(f"Filtered and sorted afternoon rates: {sorted_afternoon_rates}")

        # Select the cheapest slots
        cheapest_slots = sorted_afternoon_rates[:num_slots]
        if not cheapest_slots:
            _LOGGER.warning("No Afternoon slots available")
            return 0, 0.0, []  # Return empty values

        # Extract slot times and filter out the ones that have already passed
        slot_times = [slot["Start Time"] for slot in cheapest_slots]
        slot_times = [
            slot
            for slot in slot_times
            if datetime.strptime(slot, "%H:%M:%S").time() >= current_time
        ]

        # Check if there are any slot times left after filtering
        if not slot_times:
            _LOGGER.warning("All selected Afternoon slots have already passed.")
            return 0, 0.0, []  # Return empty values

        # Sort the remaining slot times
        slot_times.sort(key=lambda x: datetime.strptime(x, "%H:%M:%S").time())

        # Calculate total cost
        total_cost = sum(
            slot["Cost"] * (charge_rate_kwh / 2) for slot in cheapest_slots
        )

    except Exception as e:
        _LOGGER.error(f"Error in creating Afternoon charge plan: {e}")
        return 0, 0.0, []  # Return empty values in case of an error

    # Return the number of slots, total cost, and slot times
    return num_slots, total_cost, slot_times


#### evening plan #####
def create_evening_charge_plan(evening_today, num_slots, charge_rate_kwh):
    try:
        current_time = datetime.now().time()

        # Convert 'Cost' from string to float and remove the 'p' (assuming all costs end with 'p')
        for rate in evening_today:
            if isinstance(rate["Cost"], str):
                rate["Cost"] = float(rate["Cost"].rstrip("p"))

        # Filter rates for the afternoon period and below the price threshold
        _LOGGER.info("Creating evening charge plan")
        evening_rates_filtered = [
            rate for rate in evening_today if rate["Cost"] < 10.00
        ]
        # Sort rates by cost, then by datetime
        sorted_evening_rates = sorted(
            evening_rates_filtered, key=lambda x: (x["Cost"], x["Start Time"])
        )
        _LOGGER.debug(f"Filtered and sorted afternoon rates: {sorted_evening_rates}")
        # Select the cheapest slots
        cheapest_slots = sorted_evening_rates[:num_slots]
        if not cheapest_slots:
            _LOGGER.warning("No evening slots available")
            return 0, 0.0, []  # Return empty values

        # Extract slot times and filter out the ones that have already passed
        slot_times = [slot["Start Time"] for slot in cheapest_slots]
        slot_times = [
            slot
            for slot in slot_times
            if datetime.strptime(slot, "%H:%M:%S").time() >= current_time
        ]

        # Check if there are any slot times left after filtering
        if not slot_times:
            _LOGGER.warning("All selected evening slots have already passed.")
            return 0, 0.0, []  # Return empty values

        # Sort the remaining slot times
        slot_times.sort(key=lambda x: datetime.strptime(x, "%H:%M:%S").time())

        # Calculate total cost
        total_cost = sum(
            slot["Cost"] * (charge_rate_kwh / 2) for slot in cheapest_slots
        )

    except Exception as e:
        _LOGGER.error(f"Error in creating evening charge plan: {e}")
        return 0, 0.0, []  # Return empty values in case of an error

    # Return the number of slots, total cost, and slot times
    return num_slots, total_cost, slot_times


### night plan ###
def create_night_charge_plan(rates_from_midnight, num_slots, charge_rate_kwh):
    try:
        current_time = datetime.now().time()

        # Convert 'Cost' from string to float and remove the 'p' (assuming all costs end with 'p')
        for rate in rates_from_midnight:
            if isinstance(rate["Cost"], str):
                rate["Cost"] = float(rate["Cost"].rstrip("p"))

        # Filter rates for the afternoon period and below the price threshold
        _LOGGER.info("Creating night charge plan")
        night_rates_filtered = [
            rate for rate in rates_from_midnight if rate["Cost"] < 10.00
        ]

        # Sort rates by cost, then by datetime
        sorted_night_rates = sorted(
            night_rates_filtered, key=lambda x: (x["Cost"], x["Start Time"])
        )
        _LOGGER.debug(f"Filtered and sorted night rates: {sorted_night_rates}")

        # Select the cheapest slots
        cheapest_slots = sorted_night_rates[:num_slots]
        if not cheapest_slots:
            _LOGGER.warning("No Nighttime slots available")
            return 0, 0.0, []  # Return empty values

        # Extract slot times and filter out the ones that have already passed
        slot_times = [slot["Start Time"] for slot in cheapest_slots]
        slot_times = [
            slot
            for slot in slot_times
            if datetime.strptime(slot, "%H:%M:%S").time() >= current_time
        ]

        # Check if there are any slot times left after filtering
        if not slot_times:
            _LOGGER.warning("All selected Nighttime slots have already passed.")
            return 0, 0.0, []  # Return empty values

        # Sort the remaining slot times
        slot_times.sort(key=lambda x: datetime.strptime(x, "%H:%M:%S").time())

        # Calculate total cost
        total_cost = sum(
            slot["Cost"] * (charge_rate_kwh / 2) for slot in cheapest_slots
        )

    except Exception as e:
        _LOGGER.error(f"Error in creating Nighttime charge plan: {e}")
        return 0, 0.0, []  # Return empty values in case of an error

    # Return the number of slots, total cost, and slot times
    return num_slots, total_cost, slot_times


def get_current_time_period():
    now = datetime.now()
    # Define your time ranges for afternoon, evening, and night
    # Example:
    afternoon_start, afternoon_end = time(12, 0), time(16, 0)
    evening_start, evening_end = time(17, 50), time(23, 59)
    night_start, night_end = time(23, 25), time(8, 0)

    if afternoon_start <= now.time() < afternoon_end:
        _LOGGER.info("Current time period is afternoon.")
        return "afternoon"
    elif evening_start <= now.time() < evening_end:
        _LOGGER.info("Current time period is evening.")
        return "evening"
    elif night_start <= now.time() < night_end:
        _LOGGER.info("Current time period is night.")
        return "night"
    else:
        _LOGGER.info("Current time period is morning or off-peak.")
        return "outside"  # or another appropriate default


def create_charge_plan(
    capacity_kwh,
    soc_percentage,
    charge_rate_kwh,
    afternoon_today,
    evening_today,
    rates_from_midnight,
    custom_soc_percentage,
):
    # Check if necessary data is available
    if not all([capacity_kwh, soc_percentage, charge_rate_kwh]):
        raise ValueError("One or more required data elements are missing or invalid.")

    # Calculate required kWh
    required_kwh = calculate_required_kwh(
        capacity_kwh, soc_percentage, custom_soc_percentage
    )
    num_slots = math.ceil(max(required_kwh, 0) / (charge_rate_kwh / 2))

    current_time_period = get_current_time_period()

    try:
        if current_time_period == "afternoon":
            num_slots, total_cost, slot_times = create_afternoon_charge_plan(
                afternoon_today, num_slots, charge_rate_kwh
            )
        elif current_time_period == "evening":
            num_slots, total_cost, slot_times = create_evening_charge_plan(
                evening_today, num_slots, charge_rate_kwh
            )
        elif current_time_period == "night":
            num_slots, total_cost, slot_times = create_night_charge_plan(
                rates_from_midnight, num_slots, charge_rate_kwh
            )
        else:
            _LOGGER.info(
                "Outside of any predefined charge plan period. Waiting for next period."
            )
            slot_times = 0
            num_slots = 0
            total_cost = []

    except Exception as e:
        raise Exception(f"Error in creating charge plan: {e}")

    return num_slots, total_cost, slot_times
