import requests
import json
from datetime import datetime, timedelta

def get_tariff(api_key, account):
    agreements_list = []
    current_datetime = datetime.now()

    base_url = f'https://api.octopus.energy/v1/accounts/{account}/'
    response = requests.get(base_url, auth=(api_key, ''))
    data = response.json()['properties']

    for properties_item in data:
        electricity_meter_points = properties_item.get('electricity_meter_points', [])

        for meter_point in electricity_meter_points:
            agreements = meter_point.get('agreements', [])

            for agreement in agreements:
                tariff = agreement.get('tariff_code')
                valid_from = agreement.get('valid_from')
                valid_to = agreement.get('valid_to')
                is_export = meter_point.get('is_export', False)

                agreements_dict = {'tariff': tariff, 'valid_from': valid_from, 'valid_to': valid_to, 'is_export': is_export}
                agreements_list.append(agreements_dict)

    tariff_import = [
        item['tariff'] for item in agreements_list
        if item['valid_to'] is None and not item['is_export']
    ]

    if not tariff_import:
        print('No Tariff Available')
    else:
        product_code_import = [
            "-".join(tariff.split('-')[2:-1]) for tariff in tariff_import
        ]

    tariff_export = [
        item['tariff'] for item in agreements_list
        if item['valid_to'] is None and item['is_export']
    ]
    if not tariff_export:
        print('No tariff Available')
    else:
        product_code_export = [
            "-".join(tariff.split('-')[4:]) for tariff in tariff_export
        ]

    return product_code_import, product_code_export
