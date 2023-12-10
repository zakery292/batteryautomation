from homeassistant.helpers.service import async_register_admin_service
import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = "octopus_energy"

async def async_setup(hass, config):
    async_register_admin_service(
        hass, DOMAIN, "update_octopus_energy_data", async_service_handler
    )
    return True

async def async_service_handler(service_call):
    """Handle service calls."""
    entity_id = service_call.data.get("entity_id")
    if entity_id:
        entity = hass.states.get(entity_id)
        if entity and entity.domain == DOMAIN:
            entity.async_schedule_update_ha_state(True)
        else:
            _LOGGER.warning("Invalid entity_id: %s", entity_id)
    else:
        _LOGGER.warning("Missing entity_id in service call")
