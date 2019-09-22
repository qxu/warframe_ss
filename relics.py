from datetime import datetime
from decimal import Decimal
import random
import re
import os

import drops
import market


class ParseException(Exception):
    pass


def main():
    items = market.get_items()

    current_relics = []

    mission_drops = drops.get_missions()

    for location, location_data in mission_drops:
        for rotation, rotation_data in location_data:
            for drop_item, rate in rotation_data:
                if drop_item.endswith(' Relic'):
                    current_relics.append(drop_item[:-len(' Relic')])

    current_relics = sorted(set(current_relics))

    relic_drops = drops.get_relics()
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

        item = market.find_drop_item(items, drop_item)
        if item is None:
            raise RuntimeError('Could not find drop_item {}'.format(drop_item))

        price = market.get_item_price(item)
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

    with open('out/ev_relics/{}.txt'.format(datetime.now().strftime('%Y-%m-%dT%H.%M.%S')), 'w') as f:
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

    with open('out/ev_mp4_relics/{}.txt'.format(datetime.now().strftime('%Y-%m-%dT%H.%M.%S')), 'w') as f:
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

            print('{} {:.2f} {:.2f} {:.2f} {:.2f}'.format(relic, intact_ev, exceptional_ev, flawless_ev, radiant_ev))
            f.write('{} {:.2f} {:.2f} {:.2f} {:.2f}\n'.format(relic, intact_ev, exceptional_ev, flawless_ev, radiant_ev))


if __name__ == '__main__':
    main()
