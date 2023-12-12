import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta
from .get_tariff import get_tariff
import requests

_LOGGER = logging.getLogger(__name__)

current_datetime = datetime.now()
tomorrow_datetime = current_datetime + timedelta(days=1)

current_day_str = current_datetime.strftime("%d-%m-%Y")
tomorrow_str = tomorrow_datetime.strftime("%d-%m-%Y")


async def get_octopus_energy_rates(api_key, account_id, rate_type):
    current_day = datetime.now()
    tomorrow = current_day + timedelta(days=1)

    # Retrieve product codes using get_tariff function
    product_code_import, tariff_import = await get_tariff(api_key, account_id)

    if not product_code_import or not tariff_import:
        _LOGGER.error("Failed to get tariff information.")
        return []

    # Assuming product_code_import is a list, join it to create a string
    i_import = "-".join(product_code_import)
    _LOGGER.info("import: %s", i_import)
    c_import = "-".join(tariff_import)
    _LOGGER.info("product: %s", c_import)

    # Set the API url for rates based upon the data received earlier
    async with aiohttp.ClientSession() as session:
        url_import = f"https://api.octopus.energy/v1/products/{c_import}/electricity-tariffs/{i_import}/standard-unit-rates/"

        try:
            async with session.get(url_import) as response:
                response.raise_for_status()
                data = await response.json()
                rates_import = data["results"]
                # ... process rates_import ...
        except Exception as e:
            _LOGGER.error(f"Error fetching Octopus Energy rates: {e}")
            return []
    rates_list = []
    # _LOGGER.info("rates list: %s", rates_import)

    try:
        response = await asyncio.to_thread(requests.get, url_import)
        response.raise_for_status()
        rates_import = response.json()["results"]

        for item in rates_import:
            value = item["value_inc_vat"]
            valid_from = item["valid_from"]
            valid_till = item["valid_to"]

            valid_till_dt = datetime.fromisoformat(valid_till)
            valid_from_dt = datetime.fromisoformat(valid_from)

            valid_till_formatted = valid_till_dt.strftime("%H:%M:%S")
            valid_from_formatted = valid_from_dt.strftime("%H:%M:%S")
            date_formatted = valid_from_dt.strftime("%d-%m-%Y")
            # _LOGGER.info("valid from:%s", valid_from_formatted)
            # _LOGGER.info("valid TILL:%s", valid_till_formatted)

            rates_dict = {
                "Cost": str(value) + "p",
                "Date": date_formatted,
                "Start Time": valid_from_formatted,
                "End Time": valid_till_formatted,
            }
            rates_list.append(rates_dict)
            # _LOGGER.info("rates dictionaty: %s", rates_dict)

        sorted_rates = sorted(rates_list, key=lambda k: k["Start Time"])

        sorted_by_date = sorted(
            rates_list,
            key=lambda d: (
                datetime.strptime(d["Date"], "%d-%m-%Y"),
                datetime.strptime(d["Start Time"], "%H:%M:%S"),
            ),
        )

        # _LOGGER.info("sorted by date: %s", sorted_by_date)

        if rate_type == "rates_from_midnight":
            return [
                item
                for item in sorted_rates
                if item_meets_condition(
                    item, "00:00:00", "07:30:00", current_day, tomorrow
                )
            ]
        elif rate_type == "afternoon_today":
            return [
                item
                for item in sorted_rates
                if item_meets_condition(item, "12:00:00", "16:00:00", current_day)
            ]
        elif rate_type == "afternoon_tomorrow":
            return [
                item
                for item in sorted_rates
                if item_meets_condition(item, "12:00:00", "16:00:00", tomorrow)
            ]
        elif rate_type == "all_rates":
            return [
                item
                for item in sorted_by_date
                if item["Date"]
                in [
                    current_day_str,
                    tomorrow_str,
                ]
            ]
        else:
            _LOGGER.warning("Invalid rate type specified.")
            return []

    except Exception as e:
        _LOGGER.error(f"Error fetching Octopus Energy rates: {e}")
        return []


def item_meets_condition(item, start_time, end_time, *days):
    """Check if the item's valid_from falls within the specified time window on any given day."""
    item_date_time = datetime.strptime(
        item["Date"] + " " + item["Start Time"], "%d-%m-%Y %H:%M:%S"
    )
    return any(
        datetime.combine(day, datetime.strptime(start_time, "%H:%M:%S").time())
        <= item_date_time
        <= datetime.combine(day, datetime.strptime(end_time, "%H:%M:%S").time())
        for day in days
    )
