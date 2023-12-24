import sqlite3
from datetime import datetime, timedelta
import numpy as np
from sklearn.linear_model import LinearRegression
from homeassistant.core import HomeAssistant
import numpy as np
from numpy.polynomial.polynomial import Polynomial
from datetime import time, datetime, date
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

DATABASE_FILENAME = "soc_data.db"


def fetch_historical_data(hass: HomeAssistant, lookback_period: timedelta):
    db_path = hass.config.path(
        "custom_components", "battery_automation", "database", DATABASE_FILENAME
    )
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    end_time = datetime.now()
    start_time = end_time - lookback_period
    cursor.execute(
        "SELECT timestamp, soc FROM soc_data WHERE timestamp BETWEEN ? AND ?",
        (start_time, end_time),
    )
    data = cursor.fetchall()
    conn.close()

    # Define the time range to exclude for today's date
    today = datetime.now().date()
    exclude_start = datetime.combine(today, time(0, 54))
    exclude_end = datetime.combine(today, time(6, 50))

    # Exclude data between 00:54 and 06:50 only for today's date
    filtered_data = []
    for timestamp_str, soc in data:
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
        if not (exclude_start <= timestamp <= exclude_end):
            filtered_data.append((timestamp_str, soc))

    return filtered_data


def is_peak_hour(timestamp):
    return 16 <= timestamp.hour < 19  # 4 PM to 7 PM


def is_charging_period(historical_data):
    """Determine if the given period is a charging period based on consecutive SoC increases."""
    increases = 0
    for i in range(1, len(historical_data)):
        if historical_data[i][1] > historical_data[i - 1][1]:
            increases += 1
        else:
            increases = 0

        # Consider it a charging period if there are several consecutive increases
        if increases >= 2:
            return True
    return False


def predict_future_state(
    hass: HomeAssistant, prediction_horizon: timedelta, lookback_period: timedelta
):
    minimum_required_data_points = 260
    historical_data = fetch_historical_data(hass, lookback_period)

    # Check if there is enough data
    if len(historical_data) < minimum_required_data_points:
        # Not enough data, use an alternative estimation method
        return estimate_based_on_available_data(historical_data)

    # Convert datetime objects to numeric values (e.g., seconds since start of data)
    start_time = datetime.strptime(historical_data[0][0], "%Y-%m-%d %H:%M:%S.%f")
    timestamps = np.array(
        [
            (
                datetime.strptime(t[0], "%Y-%m-%d %H:%M:%S.%f") - start_time
            ).total_seconds()
            for t in historical_data
        ]
    )
    soc_values = np.array([t[1] for t in historical_data])

    # Perform linear regression using numpy
    A = np.vstack([timestamps, np.ones(len(timestamps))]).T
    m, c = np.linalg.lstsq(A, soc_values, rcond=None)[0]

    # Predict future state
    future_timestamp = (
        datetime.now() + prediction_horizon - start_time
    ).total_seconds()
    predicted_soc = m * future_timestamp + c

    # Cap the predicted SoC at 100% and format to two decimal places
    predicted_soc = min(predicted_soc, 100)
    formatted_soc = round(predicted_soc, 2)

    return formatted_soc


def predict_peak_hours_soc(hass: HomeAssistant, lookback_period: timedelta):
    # 4 PM to 7 PM in half-hour intervals, and 10 PM
    specific_hours = [time(hour=h, minute=m) for h in range(16, 19) for m in [0, 30]]
    specific_hours.append(time(hour=22, minute=0))  # Adding 10 PM

    predictions = {}
    for specific_hour in specific_hours:
        prediction_horizon = (
            datetime.combine(date.today(), specific_hour) - datetime.now()
        )
        if prediction_horizon.total_seconds() > 0:  # Only predict for future times
            predicted_soc = predict_future_state(
                hass, prediction_horizon, lookback_period
            )
            if predicted_soc is not None:
                predictions[specific_hour.strftime("%H:%M")] = predicted_soc
            else:
                # If no prediction available, estimate based on available data
                predicted_soc = estimate_based_on_available_data(hass, lookback_period)
                predictions[specific_hour.strftime("%H:%M")] = predicted_soc

    return predictions


def estimate_based_on_available_data(hass: HomeAssistant, lookback_period: timedelta):
    # Fetch available historical data
    historical_data = fetch_historical_data(hass, lookback_period)
    if len(historical_data) < 2:
        return None  # Not enough data to make any estimate

    # Simple estimation logic, e.g., average of available data
    soc_values = [data[1] for data in historical_data]  # Extract SoC values
    return sum(soc_values) / len(soc_values)  # Return average SoC
