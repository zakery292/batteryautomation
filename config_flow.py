# config_flow.py
"""Config flow for blueprint"""
import logging
import requests
import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, set_api_key_and_account, get_api_key_and_account
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

        if user_input is not None:
            api_key = user_input.get("api_key")
            account_id = user_input.get("account_id")

            # Perform API key validation here
            async with aiohttp.ClientSession() as session:
                if await validate_api_key(session, api_key, account_id):
                    # If valid, create the entry
                    set_api_key_and_account(api_key, account_id)
                    return self.async_create_entry(
                        title="Battery Automation", data=user_input
                    )
                else:
                    return self.async_show_form(
                        step_id="user",
                        errors={
                            "base": translations.get(
                                "config.step.user.errors.invalid_key"
                            )
                        },
                        data_schema=vol.Schema(
                            {
                                vol.Required("api_key", default=api_key): str,
                                vol.Required("account_id", default=account_id): str,
                            }
                        ),
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("api_key", default=""): str,
                    vol.Required("account_id", default=""): str,
                    vol.Optional("battery_sensor", default=""): str,
                }
            ),
        )

    async def async_setup_entry(self, hass, entry):
        """Set up the Battery Automation integration."""
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
