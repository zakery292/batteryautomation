import sqlite3
import logging
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from .const import DOMAIN
import os

_LOGGER = logging.getLogger(__name__)
DATABASE_FILENAME = "soc_data.db"


def init_database(hass: HomeAssistant):
    # Create the database directory if it doesn't exist
    db_directory = hass.config.path(
        "custom_components", "battery_automation", "database"
    )
    if not os.path.exists(db_directory):
        os.makedirs(db_directory)

    db_path = os.path.join(db_directory, DATABASE_FILENAME)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS soc_data
                      (timestamp DATETIME PRIMARY KEY, soc REAL)"""
    )
    conn.commit()
    conn.close()


def insert_soc_data(hass: HomeAssistant, soc: float, timestamp: datetime):
    db_path = hass.config.path(
        "custom_components", "battery_automation", "database", DATABASE_FILENAME
    )
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Include the timestamp in the insert statement
    cursor.execute(
        "INSERT INTO soc_data (timestamp, soc) VALUES (?, ?)", (timestamp, soc)
    )
    conn.commit()
    conn.close()

    # Log the insertion
    _LOGGER.info(f"Inserted SoC data: {soc} at {timestamp}")


async def collect_soc_data(hass: HomeAssistant):
    battery_charge_entity_id = hass.data[DOMAIN].get("battery_charge_entity_id")
    current_time = datetime.now()

    if battery_charge_entity_id:
        state = hass.states.get(battery_charge_entity_id)
        if state:
            try:
                current_soc = float(state.state)
                _LOGGER.info(f"Collected SoC from entity: {current_soc}")
                insert_soc_data(hass, current_soc, current_time)
            except ValueError:
                _LOGGER.error(f"Invalid SoC value: {state.state}")
                return
        else:
            _LOGGER.warning(f"Entity {battery_charge_entity_id} state not found")
            return
    else:
        _LOGGER.warning("battery_charge_entity_id not set, using global state")
        current_soc = float(hass.data[DOMAIN].get("battery_charge_state", 0))
        insert_soc_data(hass, current_soc, current_time)


def get_soc_data(hass: HomeAssistant, start_time: datetime, end_time: datetime):
    db_path = hass.config.path(
        "custom_components", "your_integration_name", DATABASE_FILENAME
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
