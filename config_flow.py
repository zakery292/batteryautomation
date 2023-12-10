from homeassistant import config_entries
import voluptuous as vol
import requests
import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = "octopus_energy"

async def async_setup_entry(hass, entry):
    # Setup the integration
    pass

class OctopusEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            api_key = user_input.get("api_key")
            account_id = user_input.get("account_id")

            # Perform API key validation here
            if await validate_api_key(api_key, account_id):
                # If valid, create the entry
                return self.async_create_entry(title="Octopus Energy", data=user_input)
            else:
                return self.async_show_form(
                    step_id="user",
                    errors={"base": "Invalid API key or account ID"},
                    data_schema=vol.Schema({
                        vol.Required("api_key"): str,
                        vol.Required("account_id"): str,
                    }),
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("api_key"): str,
                vol.Required("account_id"): str,
            }),
        )

async def validate_api_key(api_key, account_id):
    try:
        # Make a request to the Octopus API with the provided API key and account ID
        url = f'https://api.octopus.energy/v1/accounts/{account_id}/'
        response = requests.get(url, auth=(api_key, ''))
        response.raise_for_status()
        data = response.json()
        return True
    except Exception as e:
        _LOGGER.error(f"Error validating API key: {e}")
        return False
