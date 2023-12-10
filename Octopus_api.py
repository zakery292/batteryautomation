import requests
import datetime
from datetime import datetime, timedelta
from get_tariff import get_tariff  # Import the function, not variables
import logging

_LOGGER = logging.getLogger(__name__)

# Current time
current_day = datetime.now()
# Tomorrow
tomorrow = current_day + timedelta(days=1)
agreements_list = []
i = "-".join(tariff_import)
c = "-".join(product_code_import)

# Set the API url for rates based upon the data received earlier
url = f'https://api.octopus.energy/v1/products/{c}/electricity-tariffs/{i}/standard-unit-rates/'
rates_list = []

try:
    response = requests.get(url)
    response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    rates = response.json()['results']
except Exception as e:
    _LOGGER.error(f'Error fetching Octopus Energy rates: {e}')
    print('No rates available')
    exit()

for item in rates:
    value = item['value_inc_vat']
    valid_from = item['valid_from']
    valid_till = item['valid_to']

    # Convert the date time
    valid_till_dt = datetime.fromisoformat(valid_till)
    valid_from_dt = datetime.fromisoformat(valid_from)

    # Format the date time
    valid_till_formatted = valid_till_dt.strftime('%d %H:%M:%S')
    valid_from_formatted = valid_from_dt.strftime('%d %H:%M:%S')

    # Create a dictionary
    rates_dict = {'value': value, 'valid_from': valid_from_formatted, 'valid_till': valid_till_formatted}
    rates_list.append(rates_dict)

# Sort the rates by time
sorted_rates = sorted(rates_list, key=lambda k: k['valid_from'])

rates_from_midnight = [
    item for item in sorted_rates
    if (tomorrow.strftime('%d') + ' 00:00:00' <= item['valid_from'] <= tomorrow.strftime('%d') + ' 07:30:00') or
    (current_day.strftime('%d') + ' 00:00:00' <= item['valid_from'] <= current_day.strftime('%d') + ' 07:30:00')
]

if not rates_from_midnight:
    _LOGGER.warning('No Rates available')
else:
    slots_from_midnight = sorted(rates_from_midnight, key=lambda k: k['valid_from'])
    print('Rates this from Midnight:\n', slots_from_midnight)

# Afternoon Rates for the Current Day
afternoon_slots_today = [
    item for item in sorted_rates
    if current_day.strftime('%d') + ' 12:00:00' <= item['valid_from'] <= current_day.strftime('%d') + ' 16:00:00'
]

# Afternoon Rates for tomorrow
afternoon_slots_tomorrow = [
    item for item in sorted_rates
    if tomorrow.strftime('%d') + ' 12:00:00' <= item['valid_from'] <= tomorrow.strftime('%d') + ' 16:00:00'
]

# Sort afternoon rates by price Current day
afternoon_rates_today = sorted(afternoon_slots_today, key=lambda k: k['value'])

# Sort afternoon rates by price tomorrow
afternoon_rates_tomorrow = sorted(afternoon_slots_tomorrow, key=lambda k: k['value'])
(print('Afternoon rates for today:\n', afternoon_rates_today))  