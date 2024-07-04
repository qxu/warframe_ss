import csv
import json
import os

import requests
from bs4 import BeautifulSoup


DROPS_URL = 'https://www.warframe.com/droptables'


class ParseException(Exception):
    pass


soup = None


def get_soup():
    global soup

    if soup is None:
        response = requests.get(DROPS_URL)
        soup = BeautifulSoup(response.content, 'html.parser')

    return soup


def parse_table_missions(table):
    rows = table.find_all('tr', recursive=False)

    result = []

    location = None
    location_data = []
    rotation = None
    rotation_data = []

    for row in rows:
        row_class = row.get('class')
        if row_class and 'blank-row' in row_class:
            if rotation_data:
                location_data.append((rotation, rotation_data))
            if location_data:
                result.append((location, location_data))

            location = None
            location_data = []
            rotation = None
            rotation_data = []
            continue
        
        header = row.find_all('th', recursive=False)
        if header:
            if len(header) != 1:
                raise ParseException('Unexpected header length')
            if location:
                if rotation_data:
                    location_data.append((rotation, rotation_data))
                rotation = header[0].text
                rotation_data = []
            else:
                location = header[0].text
        else:
            columns = row.find_all('td', recursive=False)
            if len(columns) != 2:
                raise ParseException('Unexpected data length')
            rotation_data.append([column.text for column in columns])

    if rotation_data:
        location_data.append((rotation, rotation_data))
    if location_data:
        result.append((location, location_data))

    location = None
    location_data = []
    rotation = None
    rotation_data = []

    return result


def get_missions(nc=True, save=True):
    if nc and os.path.isfile('drops/missions.json'):
        with open('drops/missions.json') as f:
            return json.load(f)

    soup = get_soup()

    header = soup.select_one('#missionRewards')
    if header is None:
        raise ParseException('Could not get missions header')
    table = header.next_sibling.next_sibling
    if table.name != 'table':
        raise ParseException('Could not get missions table')

    missions = parse_table_missions(table)

    if save:
        if not os.path.isdir('drops'):
            os.makedirs('drops')

        with open('drops/missions.json', 'w') as f:
            json.dump(missions, f, indent=2)

        with open('drops/missions.csv', 'w') as f:
            writer = csv.writer(f)
            writer.writerow(['Location', 'Rotation', 'Item', 'Rate'])
            for location, location_data in missions:
                for rotation, rotation_data in location_data:
                    for item, rate in rotation_data:
                        writer.writerow([location, rotation, item, rate])

    return missions


def parse_table_relics(table):
    rows = table.find_all('tr', recursive=False)

    result = []

    location = None
    current_data = []

    for row in rows:
        row_class = row.get('class')
        if row_class and 'blank-row' in row_class:
            if current_data:
                result.append((location, current_data))

            location = None
            current_data = []
            continue
        
        header = row.find_all('th', recursive=False)
        if header:
            if location is not None:
                raise ParseException('Expected blank-row before header')
            if len(header) != 1:
                raise ParseException('Unexpected header length')
            location = header[0].text
        else:
            columns = row.find_all('td', recursive=False)
            if len(columns) != 2:
                raise ParseException('Unexpected data length')
            current_data.append([column.text for column in columns])

    if current_data:
        result.append((location, current_data))

    location = None
    current_data = []

    return result


def get_relics(nc=True, save=True):
    if nc and os.path.isfile('drops/relics.json'):
        with open('drops/relics.json') as f:
            return json.load(f)

    soup = get_soup()

    header = soup.select_one('#relicRewards')
    if header is None:
        raise ParseException('Could not get relics header')
    table = header.next_sibling.next_sibling
    if table.name != 'table':
        raise ParseException('Could not get relics table')

    relics = parse_table_relics(table)

    if save:
        if not os.path.isdir('drops'):
            os.makedirs('drops')

        with open('drops/relics.json', 'w') as f:
            json.dump(relics, f, indent=2)

        with open('drops/relics.csv', 'w') as f:
            writer = csv.writer(f)
            writer.writerow(['Location', 'Item', 'Rate'])
            for location, location_data in relics:
                for item, rate in location_data:
                    writer.writerow([location, item, rate])

    return relics


def save_missions(soup):
    missions = get_missions(soup)
    
    if not os.path.isdir('drops'):
        os.makedirs('drops')

    with open('drops/missions.json', 'w') as f:
        json.dump(missions, f, indent=2)
    
    with open('drops/missions.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['Location', 'Rotation', 'Item', 'Rate'])
        for location, location_data in missions:
            for rotation, rotation_data in location_data:
                for item, rate in rotation_data:
                    writer.writerow([location, rotation, item, rate])


def save_relics(soup):
    relics = get_relics(soup)

    if not os.path.isdir('drops'):
        os.makedirs('drops')

    with open('drops/relics.json', 'w') as f:
        json.dump(relics, f, indent=2)
    
    with open('drops/relics.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['Location', 'Item', 'Rate'])
        for location, location_data in relics:
            for item, rate in location_data:
                writer.writerow([location, item, rate])


def save_drops():
    get_missions(nc=False, save=True)
    get_relics(nc=False, save=True)


if __name__ == '__main__':
    save_drops()

            
