"""Define sensors for Battery Automation."""
# sensor.py
import logging
from homeassistant.helpers.entity import Entity
from .const import DOMAIN, unique_id_charging_status
from datetime import datetime, timedelta
from .sensors.octopus_energy_sensor import OctopusEnergySensor
from .sensors.battery_storage_sensor import BatteryStorageSensors
from .sensors.battery_charge_plan_sensor import BatteryChargePlanSensor
from .sensors.average_battery_usage import AverageBatteryUsageSensor
from .sensors.battery_prediction_sensor import BatteryPredictionSensor
from .sensors.peak_hours import PeakHours

_LOGGER = logging.getLogger(__name__)


async def update_charge_plan(hass):
    """Function to update the charge plan sensor."""
    charge_plan_sensor = next(
        (
            sensor
            for sensor in hass.data[DOMAIN]["sensors"]
            if isinstance(sensor, BatteryChargePlanSensor)
        ),
        None,
    )
    if charge_plan_sensor:
        await charge_plan_sensor.async_update()


class ChargingStatusSensor(Entity):
    def __init__(self, name):
        self._name = name
        self._state = "Initializing"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return f"{unique_id_charging_status}_{self._name}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_info(self):
        """Return information about the device this sensor is part of."""
        return {
            "identifiers": {(DOMAIN, "battery_storage_sensors")},
            "name": "Battery Storage Automation",
            "manufacturer": "Zakery292",
        }

    def update_state(self, new_state):
        """Update the state of the sensor."""
        self._state = new_state
        self.schedule_update_ha_state()


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup sensor platform."""
    sensors = [
        OctopusEnergySensor("Afternoon Today", "afternoon_today"),
        OctopusEnergySensor("Afternoon Tomorrow", "afternoon_tomorrow"),
        OctopusEnergySensor("Evening Today", "evening_today"),
        OctopusEnergySensor("Rates From Midnight", "rates_from_midnight"),
        OctopusEnergySensor("All Rates", "all_rates"),
        OctopusEnergySensor("Rates Left", "rates_left"),
        OctopusEnergySensor("Current Import Rate", "current_import_rate"),
        BatteryStorageSensors("Battery Kwh", "battery_capacity_kwh"),
        BatteryChargePlanSensor("Battery Charge Plan"),
        ChargingStatusSensor("Charging Status"),  # Add the charging status sensor
    ]

    # Create sensors for average usage
    average_usage_sensors = [
        AverageBatteryUsageSensor(hass, "Last Hour Usage", timedelta(hours=1), "usage"),
        AverageBatteryUsageSensor(
            hass, "Last 12 Hours Usage", timedelta(hours=12), "usage"
        ),
        AverageBatteryUsageSensor(
            hass, "Last 24 Hours Usage", timedelta(hours=24), "usage"
        ),
        AverageBatteryUsageSensor(
            hass, "Last 7 Days Usage", timedelta(days=7), "usage"
        ),
    ]

    # Create sensors for average charge
    average_charge_sensors = [
        AverageBatteryUsageSensor(
            hass, "Last Hour Charge", timedelta(hours=1), "charge"
        ),
        AverageBatteryUsageSensor(
            hass, "Last 12 Hours Charge", timedelta(hours=12), "charge"
        ),
        AverageBatteryUsageSensor(
            hass, "Last 24 Hours Charge", timedelta(hours=24), "charge"
        ),
        AverageBatteryUsageSensor(
            hass, "Last 7 Days Charge", timedelta(days=7), "charge"
        ),
    ]

    prediction_sensor_entities = [
        BatteryPredictionSensor(hass, "1 Hour Battery Prediction", timedelta(hours=1)),
        BatteryPredictionSensor(hass, "6 Hours Battery Prediction", timedelta(hours=6)),
    ]

    peak_hour_sensors = [
        PeakHours(hass, "Peak Hours Prediction", timedelta(minutes=30), "peak_hours"),
    ]

    hass.data[DOMAIN]["sensors"] = sensors
    hass.data[DOMAIN]["update_charge_plan"] = lambda: update_charge_plan(hass)
    hass.data[DOMAIN]["average_use_sensors"] = average_usage_sensors
    hass.data[DOMAIN]["average_charge_sensors"] = average_charge_sensors
    hass.data[DOMAIN]["peak_hour_sensors"] = peak_hour_sensors
    hass.data[DOMAIN]["battery_prediction_sensors"] = prediction_sensor_entities


    all_sensors = (
        sensors
        + prediction_sensor_entities
        + peak_hour_sensors
        + average_usage_sensors
        + average_charge_sensors
    )
    async_add_entities(all_sensors, True)

    hass.data[DOMAIN]["charging_status_sensor"] = next(
        (sensor for sensor in sensors if isinstance(sensor, ChargingStatusSensor)), None
    )

    charging_entity_start = entry.data.get("charging_entity_start")
    charging_entity_end = entry.data.get("charging_entity_end")
