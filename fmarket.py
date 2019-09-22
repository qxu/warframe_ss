import argparse
import re

from tabulate import tabulate

import market
import drops


def parse_relic_args(relic_args):
    relics = []

    relic_type = None
    for relic_arg in relic_args:
        relic_arg = relic_arg.upper()

        if len(relic_arg) < 2:
            raise RuntimeError('Invalid relic')

        if re.match(r'^[A-Z]$', relic_arg[1]):
            if relic_arg.startswith('L'):
                relic_type = 'Lith'
            elif relic_arg.startswith('M'):
                relic_type = 'Meso'
            elif relic_arg.startswith('N'):
                relic_type = 'Neo'
            elif relic_arg.startswith('A'):
                relic_type = 'Axi'
            else:
                raise RuntimeError('Invalid relic type')
            relic_arg = relic_arg[1:]

        relics.append('{} {}'.format(relic_type, relic_arg))

    return relics


def parse_rate(rate_str):
    rate = re.search('\(([0-9]*(\.[0-9]+)?)%\)', rate_str)
    return float(rate.group(1)) if rate else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('relics', nargs='+')
    parser.add_argument('--sort-name', action='store_true')
    parser.add_argument('--sort-price', action='store_true')
    args = parser.parse_args()

    relics = parse_relic_args(args.relics)

    relic_drops = drops.get_relics()
    relic_data_by_location = {}

    for location, location_data in relic_drops:
        if location in relic_data_by_location:
            raise RuntimeError('Duplicate location')

        relic_data_by_location[location] = location_data

    items = market.get_items()

    rows = []

    for relic in relics:
        location = relic + ' Relic (Intact)'

        location_data = relic_data_by_location[location]

        for drop_item, rate_str in location_data:
            if drop_item == 'Forma Blueprint':
                rows.append([location, drop_item, rate_str, -1])
                continue

            item = market.find_drop_item(items, drop_item)
            if item is None:
                raise RuntimeError('Could not find drop_item {}'.format(drop_item))

            price = market.get_item_price(item)

            rows.append([location, drop_item, rate_str, price])

    if args.sort_name:
        rows.sort(key=lambda row: row[1])
    elif args.sort_price:
        rows.sort(key=lambda row: row[3], reverse=True)
    else:
        rows.sort(key=lambda row: (parse_rate(row[2]), row[2], -row[3]))
    print(tabulate(rows, headers=['Location', 'Drop', 'Rate', 'Price']))


if __name__ == '__main__':
    main()

