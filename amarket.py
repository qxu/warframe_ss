from decimal import Decimal
from datetime import datetime, timedelta
import csv
import json
import os
import re
import time
import random

import requests

import drops


class ParseException(Exception):
    pass


ITEMS_URL = 'https://api.warframe.market/v1/items'

STATISTICS_URL_FORMAT = 'https://api.warframe.market/v1/items/{}/statistics'

FILENAME_TIME_FORMAT = '%Y-%m-%dT%H.%M.%S.json'


def get_items(nc=True, save=True):
    if nc and os.path.isfile('market/items.json'):
        with open('market/items.json') as f:
            return json.load(f)

    response = requests.get(ITEMS_URL)
    items = response.json()

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
    items = items['payload']['items']['en']

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


def main():
    items = get_items()

    current_relics = []

    mission_drops = drops.get_missions()

    for location, location_data in mission_drops:
        for rotation, rotation_data in location_data:
            for drop_item, rate in rotation_data:
                if drop_item.endswith(' Relic'):
                    current_relics.append(drop_item[:-len(' Relic')])

    # current_relics = sorted(set(current_relics))

    relic_drops = drops.get_relics()
    current_relics = sorted(set(location[:location.index(' Relic')] for location, location_data in relic_drops))
    relic_data_by_location = {}

    for location, location_data in relic_drops:
        if location in relic_data_by_location:
            raise RuntimeError('Duplicate location')

        relic_data_by_location[location] = location_data

    price_by_drop_item = {}
    def get_drop_item_price(drop_item):
        price = price_by_drop_item.get(drop_item)
        if price is not None:
            return price

        item = find_drop_item(items, drop_item)
        if item is None:
            raise RuntimeError('Could not find drop_item {}'.format(drop_item))

        price = get_item_price(item)
        return price

    rate_by_rate_str = {}
    def get_rate(rate_str):
        rate = rate_by_rate_str.get(rate_str)
        if rate is not None:
            return rate
        
        rate_match = re.search(r'\(([0-9]*.[0-9]*)%\)', rate_str)
        if rate_match:
            rate = rate_match.group(1)
            rate = Decimal(rate) / Decimal(100)
        else:
            raise ParseException('Could not parse rate')
        
        rate_by_rate_str[rate_str] = rate
        return rate


    if not os.path.isdir('out/ev_relics'):
        os.makedirs('out/ev_relics')

    with open('out/ev_relics/a{}.txt'.format(datetime.now().strftime('%Y-%m-%dT%H.%M.%S')), 'w') as f:
        for relic in current_relics:
            def get_expected_value(location, debug=False):
                location_data = relic_data_by_location[location]

                expected_value = 0.0
                total_rate = Decimal()

                for drop_item, rate_str in location_data:
                    if drop_item == 'Forma Blueprint':
                        continue

                    rate = get_rate(rate_str)
                    price = get_drop_item_price(drop_item)

                    total_rate += rate
                    expected_value += price * float(rate)

                    if debug:
                        print(location, drop_item, rate, price)

                if total_rate <= 0.5:
                    raise RuntimeError('Bad total_rate')

                return expected_value

            intact_location = relic + ' Relic (Intact)'
            exceptional_location = relic + ' Relic (Exceptional)'
            flawless_location = relic + ' Relic (Flawless)'
            radiant_location = relic + ' Relic (Radiant)'

            intact_ev = get_expected_value(intact_location)
            exceptional_ev = get_expected_value(exceptional_location)
            flawless_ev = get_expected_value(flawless_location)
            radiant_ev = get_expected_value(radiant_location)

            print('{} {:.2f} {:.2f} {:.2f} {:.2f}'.format(relic, intact_ev, exceptional_ev, flawless_ev, radiant_ev))
            f.write('{} {:.2f} {:.2f} {:.2f} {:.2f}\n'.format(relic, intact_ev, exceptional_ev, flawless_ev, radiant_ev))

    if not os.path.isdir('out/ev_mp4_relics'):
        os.makedirs('out/ev_mp4_relics')

    with open('out/ev_mp4_relics/a{}.txt'.format(datetime.now().strftime('%Y-%m-%dT%H.%M.%S')), 'w') as f:
        for relic in current_relics:
            def get_multiplayer_ev(location, num_players=4, trials=4096, debug=False):
                location_data = relic_data_by_location[location]

                total_value = Decimal()

                actual_trials = 0

                for _ in range(trials):
                    best_price = None

                    for _ in range(num_players):
                        roll = random.random()
                        cumulative_rate = Decimal()

                        for drop_item, rate_str in location_data:
                            if drop_item == 'Forma Blueprint':
                                continue

                            rate = get_rate(rate_str)

                            cumulative_rate += rate
                            
                            if cumulative_rate > roll:
                                price = get_drop_item_price(drop_item)
                                if best_price is None or price > best_price:
                                    best_price = price

                        if best_price is not None:
                            actual_trials += 1
                            total_value += Decimal(str(best_price))

                return float(total_value) / actual_trials

            intact_location = relic + ' Relic (Intact)'
            exceptional_location = relic + ' Relic (Exceptional)'
            flawless_location = relic + ' Relic (Flawless)'
            radiant_location = relic + ' Relic (Radiant)'

            intact_ev = get_multiplayer_ev(intact_location)
            exceptional_ev = get_multiplayer_ev(exceptional_location)
            flawless_ev = get_multiplayer_ev(flawless_location)
            radiant_ev = get_multiplayer_ev(radiant_location)

            f.write('{} {:.2f} {:.2f} {:.2f} {:.2f}\n'.format(relic, intact_ev, exceptional_ev, flawless_ev, radiant_ev))


if __name__ == '__main__':
    main()
