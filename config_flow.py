# config_flow.py
"""Config flow"""
import logging
import voluptuous as vol
from homeassistant import config_entries, core
from .const import DOMAIN, set_api_key_and_account
import json
import os
import aiohttp

_LOGGER = logging.getLogger(__name__)

LANGUAGES_FOLDER = os.path.join(os.path.dirname(__file__), "translations")


def load_translations(lang):
    path = os.path.join(LANGUAGES_FOLDER, f"{lang}.json")
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


class BatteryAutomationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        translations = load_translations(self.hass.config.language)

        battery_charge = [
            entity.entity_id
            for entity in self.hass.states.async_all()
            if "battery" in entity.entity_id
            or entity.attributes.get("device_class") == "battery"
        ]
        battery_capacity = [
            entity.entity_id
            for entity in self.hass.states.async_all()
            if "capacity" in entity.entity_id
            or entity.attributes.get("device_class") == "battery"
        ]
        ac_charge = [
            entity.entity_id
            for entity in self.hass.states.async_all()
            if "charge" in entity.entity_id
            or entity.attributes.get("device_class") == "switch"
        ]
        charge_start = [
            entity.entity_id
            for entity in self.hass.states.async_all()
            if "charge" in entity.entity_id
            or entity.attributes.get("device_class") == "battery"
        ]
        charge_end = [
            entity.entity_id
            for entity in self.hass.states.async_all()
            if "charge" in entity.entity_id
            or entity.attributes.get("device_class") == "battery"
        ]

        if user_input is not None:
            api_key = user_input.get("api_key")
            account_id = user_input.get("account_id")
            battery_charge_rate = user_input.get("battery_charge_rate")
            _LOGGER.info(
                f"battery_charge_rate is an integer: {isinstance(battery_charge_rate, int)}"
            )

            async with aiohttp.ClientSession() as session:
                if await validate_api_key(session, api_key, account_id):
                    set_api_key_and_account(api_key, account_id)
                    return self.async_create_entry(
                        title="Battery Automation", data=user_input
                    )
                else:
                    errors = {
                        "base": translations.get("config.step.user.errors.invalid_key")
                    }
        else:
            errors = None

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional("api_key", default=""): str,
                    vol.Optional("account_id", default=""): str,
                    vol.Optional("battery_charge_rate", default=""): int,
                    vol.Optional("battery_charge"): vol.In(battery_charge),
                    vol.Optional("battery_capacity"): vol.In(battery_capacity),
                    vol.Optional("ac_charge"): vol.In(ac_charge),
                    vol.Optional("charge_start"): vol.In(charge_start),
                    vol.Optional("charge_end"): vol.In(charge_end),
                }
            ),
            errors=errors,
        )

    async def async_setup_entry(self, hass, entry):
        _LOGGER.info("Battery Automation integration is being set up.")
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, "sensor")
        )
        return True


async def validate_api_key(session, api_key, account_id):
    try:
        url = f"https://api.octopus.energy/v1/accounts/{account_id}/"
        async with session.get(url, auth=aiohttp.BasicAuth(api_key, "")) as response:
            response.raise_for_status()
            data = await response.json()
            return True
    except Exception as e:
        _LOGGER.error(f"Error validating API key: {e}")
        return False
