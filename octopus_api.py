# octopus_api.py
import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta
from .get_tariff import get_tariff

_LOGGER = logging.getLogger(__name__)

# Global variable to store rates
rates_data = {}


async def get_octopus_energy_rates(api_key, account_id, rate_type):
    current_day = datetime.now()
    tomorrow = current_day + timedelta(days=1)
    current_day_str = current_day.strftime("%d-%m-%Y")
    tomorrow_str = tomorrow.strftime("%d-%m-%Y")

    # Retrieve product codes using get_tariff function
    product_code_import, tariff_import = await get_tariff(api_key, account_id)

    if not product_code_import or not tariff_import:
        _LOGGER.error("Failed to get tariff information.")
        return None

    i_import = "-".join(product_code_import)
    c_import = "-".join(tariff_import)
    url_import = f"https://api.octopus.energy/v1/products/{c_import}/electricity-tariffs/{i_import}/standard-unit-rates/"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url_import) as response:
                response.raise_for_status()
                data = await response.json()
                rates_import = data["results"]

                # Process and store rates
                process_and_store_rates(
                    rates_import,
                    rate_type,
                    current_day,
                    tomorrow,
                    current_day_str,
                    tomorrow_str,
                )
    except Exception as e:
        _LOGGER.error(f"Error fetching Octopus Energy rates: {e}")
        return None

    # Return the requested rates data
    return rates_data.get(rate_type)


def process_and_store_rates(
    rates_import, rate_type, current_day, tomorrow, current_day_str, tomorrow_str
):
    rates_list = []

    for item in rates_import:
        value = item["value_inc_vat"]
        valid_from = item["valid_from"]
        valid_till = item["valid_to"]

        valid_till_dt = datetime.fromisoformat(valid_till)
        valid_from_dt = datetime.fromisoformat(valid_from)

        valid_till_formatted = valid_till_dt.strftime("%H:%M:%S")
        valid_from_formatted = valid_from_dt.strftime("%H:%M:%S")
        date_formatted = valid_from_dt.strftime("%d-%m-%Y")

        rates_dict = {
            "Cost": str(value) + "p",
            "Date": date_formatted,
            "Start Time": valid_from_formatted,
            "End Time": valid_till_formatted,
        }
        rates_list.append(rates_dict)

    sorted_rates = sorted(rates_list, key=lambda k: k["Start Time"])
    sorted_by_date = sorted(
        rates_list,
        key=lambda d: (
            datetime.strptime(d["Date"], "%d-%m-%Y"),
            datetime.strptime(d["Start Time"], "%H:%M:%S"),
        ),
    )
    # _LOGGER.info("rates list: %s", list)
    if rate_type == "rates_from_midnight":
        rates_data["rates_from_midnight"] = [
            item
            for item in sorted_rates
            if item_meets_condition(item, "00:00:00", "08:00:00", current_day, tomorrow)
        ]
        # _LOGGER.info(f"Rates from midnight: {rates_data['rates_from_midnight']}")  # Log specific rate data
        return

    elif rate_type == "afternoon_today":
        rates_data["afternoon_today"] = [
            item
            for item in sorted_rates
            if item_meets_condition(item, "12:00:00", "16:00:00", current_day)
        ]
        return

    elif rate_type == "afternoon_tomorrow":
        rates_data["afternoon_tomorrow"] = [
            item
            for item in sorted_rates
            if item_meets_condition(item, "12:00:00", "16:00:00", tomorrow)
        ]
        # _LOGGER.info(f"Rates Afternoon Tomorrow: {rates_data['afternoon_tomorrow']}")
        return
    elif rate_type == "all_rates":
        rates_data["all_rates"] = [
            item
            for item in sorted_by_date
            if item["Date"]
            in [
                current_day_str,
                tomorrow_str,
            ]
        ]
        return
    elif rate_type == "current_import_rate":
        now = datetime.now()
        current_rate = next(
            (
                item
                for item in sorted_by_date
                if now
                >= datetime.strptime(
                    item["Date"] + " " + item["Start Time"], "%d-%m-%Y %H:%M:%S"
                )
                and now
                < datetime.strptime(
                    item["Date"] + " " + item["End Time"], "%d-%m-%Y %H:%M:%S"
                )
            ),
            None,
        )
        rates_data["current_import_rate"] = [current_rate] if current_rate else []
        _LOGGER.info(f"current import: {rates_data['current_import_rate']}")
        return

    elif rate_type == "rates_left":
        now = datetime.now()
        future_rates = [
            item
            for item in sorted_by_date
            if now
            < datetime.strptime(
                item["Date"] + " " + item["End Time"], "%d-%m-%Y %H:%M:%S"
            )
        ]
        future_rates_sorted = sorted(
            future_rates,
            key=lambda x: datetime.strptime(
                x["Date"] + " " + x["Start Time"], "%d-%m-%Y %H:%M:%S"
            ),
        )
        rates_data["rates_left"] = future_rates_sorted
        return
        # Add other rate types as needed
    #_LOGGER.info("rates data:%s", rates_data)




def item_meets_condition(item, start_time, end_time, current_day, tomorrow=None):
    if tomorrow is None:
        tomorrow = current_day
    item_date_time = datetime.strptime(
        item["Date"] + " " + item["Start Time"], "%d-%m-%Y %H:%M:%S"
    )
    return any(
        datetime.combine(day, datetime.strptime(start_time, "%H:%M:%S").time())
        <= item_date_time
        <= datetime.combine(day, datetime.strptime(end_time, "%H:%M:%S").time())
        for day in [current_day, tomorrow]
    )


# _LOGGER.info("rates Global: %s", rates_data)

# Additional functions if needed
