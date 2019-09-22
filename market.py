from datetime import datetime, timedelta
import csv
import json
import os
import re
import time

import requests


class ParseException(Exception):
    pass


ITEMS_URL = 'https://warframe.market'

STATISTICS_URL_FORMAT = 'https://api.warframe.market/v1/items/{}/statistics'

FILENAME_TIME_FORMAT = '%Y-%m-%dT%H.%M.%S.json'


def get_items(nc=True, save=True):
    if nc and os.path.isfile('market/items.json'):
        with open('market/items.json') as f:
            return json.load(f)

    text = requests.get(ITEMS_URL).text
    json_begin_tag = '<script type="application/json" id="application-state">'
    json_begin = text.index(json_begin_tag) + len(json_begin_tag)
    json_end_tag = '</script>'
    json_end = text.index(json_end_tag, json_begin)
    data = json.loads(text[json_begin:json_end])
    items = data['items']

    if save:
        if not os.path.isdir('market'):
            os.makedirs('market')

        with open('market/items.json', 'w') as f:
            json.dump(items, f, indent=2)

    return items


def get_stats(item, nc_delta=timedelta(days=1), save=True):
    url_name = item['url_name']
    if not re.match('^[A-Za-z0-9_]+$', url_name):
        raise RuntimeError('Invalid url_name {}'.format(url_name))

    stats_path = 'market/items/{}/statistics'.format(url_name)
    if not os.path.isdir(stats_path):
        os.makedirs(stats_path)

    latest_time = None
    latest_path = None
    for filename in os.listdir(stats_path):
        path = os.path.join(stats_path, filename)
        if not os.path.isfile(path):
            continue
        try:
            file_time = datetime.strptime(filename, FILENAME_TIME_FORMAT)
        except ValueError:
            raise
        if latest_time is None or file_time > latest_time:
            latest_time = file_time
            latest_path = path

    if latest_path is None or nc_delta is None or datetime.utcnow() - nc_delta > latest_time:
        save_time = datetime.utcnow()
        response = requests.get(STATISTICS_URL_FORMAT.format(url_name))
        stats = response.json()

        time.sleep(0.5)

        if save:
            path = os.path.join(stats_path, save_time.strftime(FILENAME_TIME_FORMAT))
            with open(path, 'w') as f:
                json.dump(stats, f, indent=2)
    else:
        with open(latest_path) as f:
            stats = json.load(f)

    return stats


DROP_ITEM_NAME_MAP = {
    'Kavasa Prime Kubrow Collar Blueprint': 'Kavasa Prime Collar Blueprint',
    'Kavasa Prime Buckle': 'Kavasa Prime Collar Buckle',
    'Kavasa Prime Band': 'Kavasa Prime Collar Band'
}

def find_drop_item(items, drop_item):
    # items = items['payload']['items']['en']

    for item in items:
        if item['item_name'] == drop_item:
            return item

    if drop_item in DROP_ITEM_NAME_MAP:
        drop_item = DROP_ITEM_NAME_MAP[drop_item]
    elif drop_item.endswith(' Blueprint'):
        drop_item = drop_item[:-len(' Blueprint')]
    else:
        return

    for item in items:
        if item['item_name'] == drop_item:
            return item


def get_stats_price(stats):
    daily_entries = stats['payload']['statistics_closed']['90days']

    last_entry = None
    last_entry_datetime = None

    for entry in daily_entries:
        entry_datetime = entry['datetime']
        if not entry_datetime.endswith('.000+00:00'):
            raise ParseException('datetime')
        entry_datetime = entry_datetime[:-len('.000+00:00')]
        entry_datetime = datetime.strptime(entry_datetime, '%Y-%m-%dT%H:%M:%S')

        if last_entry_datetime is None or entry_datetime > last_entry_datetime:
            last_entry = entry
            last_entry_datetime = entry_datetime

    if last_entry is None:
        return None
    
    return last_entry['median']


price_by_url_name = {}

def get_item_price(item, memoize=True):
    global price_by_url_name
    if memoize:
        url_name = item['url_name']
        price = price_by_url_name.get(url_name)
        if price is not None:
            return price

    stats = get_stats(item)
    price = get_stats_price(stats)

    if memoize:
        price_by_url_name[url_name] = price

    return price


if __name__ == '__main__':
    get_items(nc=False)
