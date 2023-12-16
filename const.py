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


