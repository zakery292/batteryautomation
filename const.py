"""Constants for battery_automation"""

from logging import Logger, getLogger

Logger: Logger = getLogger(__package__)

DOMAIN = "battery_automation"  # noqa: D100

# Global variables to store API key and account ID
api_key = ""
account_id = ""
battery_capacity = ""
battery_entity = ""


def set_api_key_and_account(key, account):
    global api_key, account_id
    api_key = key
    account_id = account


def get_api_key_and_account():
    return api_key, account_id


def set_battery_capacity(battery_capacity_ah):
    battery_capacity = battery_capacity_ah


unique_id_battery_sensor = "battery_sensor"
unique_id_charge_plan_sensor = "charge_plan_sensor"
unique_id_charging_control_switch = "charge_control_switch"
unique_id_custom_soc_percentage = "custom_soc_percentage"
unique_id_charging_status = "custom_charging_status"
unique_id_average_battery_usage = "average_battery_usage"
unique_id_battery_predicitons = "battery_prediciton_sensor"
unique_id_peak_hours = "[peak_hours]"
unique_id_lookback = "lookback"
