import sqlite3
import logging
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from .const import DOMAIN
import os

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
