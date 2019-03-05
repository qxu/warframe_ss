import csv
import json

import requests
from bs4 import BeautifulSoup


MISSIONS_URL = 'https://docs.google.com/feeds/download/spreadsheets/Export?gid=0&key=1iyuQXUaWcIr1-DrYsFgsPsGuGANTwWDEK9Fy_fzFfLU&exportFormat=csv'

RELICS_URL = 'https://docs.google.com/feeds/download/spreadsheets/Export?gid=983656373&key=1iyuQXUaWcIr1-DrYsFgsPsGuGANTwWDEK9Fy_fzFfLU&exportFormat=csv'

KEYS_URL = 'https://docs.google.com/feeds/download/spreadsheets/Export?gid=2115252437&key=1iyuQXUaWcIr1-DrYsFgsPsGuGANTwWDEK9Fy_fzFfLU&exportFormat=csv'


DYNAMIC_LOCATIONS_URL = 1677193611

BOUNTIES_URL = 170803411


class ParseException(Exception):
    pass


            
