# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
from decimal import Decimal
import time
import requests
import logging
import dateutil.parser
from lxml import etree
import calendar
import email.utils as eut
import traceback
import os
import stat

logfile = '/var/log/pydsn/dsn.log'
app = 'parser'
# logging.basicConfig(filename=logfile, level=logging.INFO)
logging.basicConfig(
    filename=logfile,
    filemode='a',
    level=logging.INFO,
    format="%(asctime)s :: %(process)s :: %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S')

LOCAL_DEBUG = False

dsn_data_file = '/tmp/pydsn/dsn.data.xml'
dsn_config_file = '/tmp/pydsn/dsn.config.xml'


def to_decimal(value):
    # if value == '' or value == 'null':
    if value in ('', 'null', 'none', 'NaN'):
        return None
    return Decimal(value)


def to_float(value):
    if value in ('', 'null', 'none', 'NaN'):
        return None
    return float(value)


def to_int(value):
    if value in ('', 'null', 'none', 'NaN'):
        return None
    return int(value)


def filter_value(value, exclusions):
    if value in exclusions:
        return None
    return value


def file_age_in_seconds(pathname):
    return int(time.time() - os.stat(pathname)[stat.ST_MTIME])


class DSNParser(object):

    def __init__(self):
        self.stdout_path = logfile
        self.stderr_path = logfile
        self.log = logging.getLogger(__name__)
        self.http_session = requests.Session()

    def get_url(self):
        return "http://eyes.nasa.gov/dsn/data/dsn.xml?r=%s" % (int)(time.time() / 5)

    def get_config_url(self):
        return "http://eyes.nasa.gov/dsn/config.xml"

    def fetch_data(self):

        get_data = True
        # If a local dsn_data_file exists that is less than 10 seconds old use
        # that data
        if os.path.isfile(dsn_data_file):
            file_age = file_age_in_seconds(dsn_data_file)
            if file_age < 10:
                get_data = False
                self.log.info('%s :: using local data xml file - %s seconds old' % (app, str(file_age)))
            else:
                self.log.info('%s :: not using local data xml file - %s seconds old' % (app, str(file_age)))
        else:
            self.log.info('%s :: not using local data xml file - %s - not found' % (app, str(dsn_data_file)))

        if get_data:
            url = self.get_url()
            if LOCAL_DEBUG:
                self.log.info('%s :: fetching data from - %s' % (app, url))
            try:
                response = self.http_session.get(url)
                responsetime = eut.parsedate(response.headers['date'])
                responsesec = calendar.timegm(responsetime)
                self.log.info('%s :: response date: %s -> %d (%d)' % (app, response.headers['date'], responsesec, int(responsesec / 5)))
            except:
                self.log.info('%s' % (traceback.format_exc()))
                self.log.info('error :: %s :: failed to get URL - %s' % (app, str(url)))
                response = 'None'
                return None

            if str(response.content) == '<dsn><timestamp>NaN</timestamp></dsn>':
                self.log.info('error :: %s :: NASA responded with no dsn data in the XML' % (app))
                return None

            # @added 20160902 - Task #1616: Merge russss and odysseus654
            # Write the content out to file so that it can be used by dbsync
            try:
                with open(dsn_data_file, 'w') as fh:
                    fh.write(response.content)
            except:
                self.log.info('error :: %s :: failed to write response to - %s' % (app, dsn_data_file))

            doc = etree.fromstring(response.content)
        else:
            with open(dsn_data_file, 'r') as f:
                doc = etree.fromstring(f.read())

        dishes = doc.xpath('/dsn/dish')
        result = {}
        for dish in dishes:
            dish_name, data = self.parse_dish(dish)
            result[dish_name] = data
        return result

    def parse_station(self, station):
        data = {
            'friendly_name': station.get('friendlyName'),
            'time_utc': to_int(station.get('timeUTC')),
            'time_zone_offset': to_int(station.get('timeZoneOffset'))
        }
        return station.get('name'), data

    def parse_dish(self, dish):
        data = {
            'azimuth_angle': to_decimal(dish.get('azimuthAngle')),       # Degrees
            'elevation_angle': to_decimal(dish.get('elevationAngle')),   # Degrees
            'wind_speed': to_decimal(dish.get('windSpeed')),             # km/h
            'mspa': dish.get('isMSPA') == 'true',                   # Multiple Spacecraft Per Aperture
            'array': dish.get('isArray') == 'true',                 # Dish is arrayed
            'ddor': dish.get('isDDOR') == 'true',                   # Delta-Differenced One Way Range
            'created': dateutil.parser.parse(dish.get('created')),
            'updated': dateutil.parser.parse(dish.get('updated')),
            'targets': {},
            'up_signal': [],
            'down_signal': []
        }
        for target in dish.findall('target'):
            name, target_data = self.parse_target(target)
            data['targets'][name] = target_data

        for up_signal in dish.findall('upSignal'):
            data['up_signal'].append(self.parse_signal(up_signal))

        for down_signal in dish.findall('downSignal'):
            data['down_signal'].append(self.parse_signal(down_signal))

        if 'DSN' in data['targets']:
            # A target of 'DSN' seems to indicate that the dish is out of service
            data['targets'] = {}
            data['up_signal'] = []
            data['down_signal'] = []
            data['online'] = False
        else:
            data['online'] = True

        return dish.get('name'), data

    def parse_target(self, target):
        data = {
            'id': int(target.get('id')),
            'up_range': Decimal(target.get('uplegRange')),        # Up leg range, kilometers
            'down_range': Decimal(target.get('downlegRange')),    # Down leg range, kilometers
            'rtlt': Decimal(target.get('rtlt'))                   # Round-trip light time, in seconds
        }
        return target.get('name'), data

    def parse_signal(self, signal):
        if signal.get('spacecraft') == 'DSN':
            # DSN is a bogus spacecraft
            return None
        data = {
            'type': signal.get('signalType'),                   # "data", "carrier", "ranging", or "none"
            'debug': signal.get('signalTypeDebug'),             # Interesting signal debug info
            'spacecraft': signal.get('spacecraft')
        }

        if signal.get('power') == '':
            data['power'] = None
        else:
            data['power'] = to_decimal(signal.get('power'))    # Power (in dBm for downlink, kW for uplink.)

        if signal.get('frequency') == '' or signal.get('frequency') == 'none':
            data['frequency'] = None
        else:
            data['frequency'] = to_decimal(signal.get('frequency'))   # Frequency (Hz). Always present but may be wrong if type is none

        if signal.get('dataRate') == '':
            data['data_rate'] = None
        else:
            data['data_rate'] = to_decimal(signal.get('dataRate'))    # Data rate, bits per second

        return data

    def fetch_config(self):
        get_config = True
        # If a local dsn_data_file exists that is less than 10 seconds old use
        # that data
        if os.path.isfile(dsn_config_file):
            file_age = file_age_in_seconds(dsn_config_file)
            if file_age < 600:
                get_config = False
                self.log.info('%s :: using local config xml file - %s seconds old' % (app, str(file_age)))
            else:
                self.log.info('%s :: not using local config xml file - %s seconds old' % (app, str(file_age)))
        else:
            self.log.info('%s :: not using local config xml file - %s - not found' % (app, str(dsn_data_file)))

        if get_config:
            url = self.get_config_url()
            # self.log.debug("Fetching config %s" % url)
            self.log.info('%s :: fetching config from - %s' % (app, url))
            response = self.http_session.get(url)

            # @added 20160902 - Task #1616: Merge russss and odysseus654
            # Write the content out to file so that it can be used by dbsync
            try:
                with open(dsn_config_file, 'w') as fh:
                    fh.write(response.content)
            except:
                self.log.info('error :: %s :: failed to write response to - %s' % (app, dsn_config_file))
            doc = etree.fromstring(response.content)
        else:
            with open(dsn_config_file, 'r') as f:
                doc = etree.fromstring(f.read())

        spacecraft = self.fetch_spacecraft(doc.xpath('/config/spacecraftMap/spacecraft'))
        sites = self.fetch_sites(doc.xpath('/config/sites/site'))
        return sites, spacecraft

    def fetch_spacecraft(self, spacecraft):
        data = {}
        for craft in spacecraft:
            data[craft.get('name')] = craft.get('friendlyName')
        return data

    def fetch_sites(self, sites):
        data = {}
        for site in sites:
            dishes = {}
            for dish in site.findall('dish'):
                dishes[dish.get('name')] = {
                    'friendly_name': dish.get('friendlyName'),
                    'type': dish.get('type')
                }
            data[site.get('name')] = {
                'friendly_name': site.get('friendlyName'),
                'dishes': dishes
            }
        return data

if __name__ == '__main__':
    parser = DSNParser()
    from pprint import pprint
    pprint(parser.fetch_data())
