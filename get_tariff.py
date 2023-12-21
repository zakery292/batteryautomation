import requests
import json
import asyncio
from datetime import datetime, timedelta
import logging
from .const import get_api_key_and_account

_LOGGER = logging.getLogger(__name__)

_LOGGER.info("Starting get tariff")


async def get_tariff(api_key, account_id):
    try:
        # Get API key and account ID from global constants
        api_key, account_id = get_api_key_and_account()
        # _LOGGER.info("API key for get_tariff call: %s", api_key)
        url = f"https://api.octopus.energy/v1/accounts/{account_id}/"

        # Use asyncio.to_thread to perform the blocking call in a separate thread
        response = await asyncio.to_thread(requests.get, url, auth=(api_key, ""))
        response.raise_for_status()
        data = response.json()["properties"]

        agreements_list = []

        for properties_item in data:
            electricity_meter_points = properties_item.get(
                "electricity_meter_points", []
            )

            for meter_point in electricity_meter_points:
                agreements = meter_point.get("agreements", [])

                for agreement in agreements:
                    tariff = agreement.get("tariff_code")
                    valid_from = agreement.get("valid_from")
                    valid_to = agreement.get("valid_to")
                    is_export = meter_point.get("is_export", False)

                    agreements_dict = {
                        "tariff": tariff,
                        "valid_from": valid_from,
                        "valid_to": valid_to,
                        "is_export": is_export,
                    }
                    agreements_list.append(agreements_dict)

        # Extracting import tariffs and their product codes
        tariff_import = [
            item["tariff"]
            for item in agreements_list
            if item["valid_to"] is None and not item["is_export"]
        ]
        # _LOGGER.info("get tariff logger import: %s", tariff_import)
        if not tariff_import:
            _LOGGER.warning("No import tariff available.")
            return None, None

        product_code_import = [
            "-".join(tariff.split("-")[2:-1]) for tariff in tariff_import
        ]

        # _LOGGER.debug("tariff_import: %s", tariff_import)
        # _LOGGER.debug("product_code_import: %s", product_code_import)

        # Return only the import tariffs and their product codes
        return tariff_import, product_code_import

    except Exception as e:
        _LOGGER.error(f"Error retrieving tariff: {e}", exc_info=True)
        return None, None
    finally:
        _LOGGER.info("get_tariff finished")
