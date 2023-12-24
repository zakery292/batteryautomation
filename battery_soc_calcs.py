import sqlite3
import logging
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from .const import DOMAIN
import os
import sqlite3


_LOGGER = logging.getLogger(__name__)
DATABASE_FILENAME = "soc_data.db"


### Data Retreval function ###
def get_soc_data(hass: HomeAssistant, start_time: datetime, end_time: datetime):
    db_path = hass.config.path(
        "custom_components", "battery_automation", "database", DATABASE_FILENAME
    )
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT timestamp, soc FROM soc_data WHERE timestamp BETWEEN ? AND ?",
        (start_time, end_time),
    )
    data = cursor.fetchall()
    conn.close()

    return data


#### Avererage Decline ####
def calculate_average_decline(hass: HomeAssistant, period: timedelta):
    end_time = datetime.now()
    start_time = end_time - period
    soc_data = get_soc_data(hass, start_time, end_time)

    if len(soc_data) < 2:
        _LOGGER.warning("Not enough data to calculate average decline")
        return None

    total_decline = 0
    decline_intervals = 0

    for i in range(1, len(soc_data)):
        # Calculate the change between each consecutive reading
        change = soc_data[i - 1][1] - soc_data[i][1]  # soc_data[i][1] is the SoC value

        # Only consider decline periods
        if change > 0:
            total_decline += change
            decline_intervals += 1

    if decline_intervals > 0:
        average_decline = total_decline / decline_intervals
    else:
        return "Not enough decline data"

    return average_decline


def calculate_average_change(hass: HomeAssistant, period: timedelta):
    end_time = datetime.now()
    start_time = end_time - period
    soc_data = get_soc_data(hass, start_time, end_time)

    if len(soc_data) < 2:
        _LOGGER.warning("Not enough data to calculate average change")
        return None, None

    total_increase = 0
    increase_count = 0
    total_decrease = 0
    decrease_count = 0

    for i in range(1, len(soc_data)):
        change = soc_data[i][1] - soc_data[i - 1][1]

        if change > 0:  # Increase in SoC
            total_increase += change
            increase_count += 1
        elif change < 0:  # Decrease in SoC
            total_decrease += abs(change)  # Use absolute value for decrease
            decrease_count += 1

    average_increase = round((total_increase / increase_count) if increase_count > 0 else 0, 2)
    average_decrease = round((total_decrease / decrease_count) if decrease_count > 0 else 0, 2)

    # Ensure the maximum charge does not exceed 100%
    average_increase = min(average_increase, 100)

    return average_increase, average_decrease
