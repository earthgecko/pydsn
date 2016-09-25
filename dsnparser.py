# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
import calendar
import dateutil.parser
import email.utils as eut
import logging
from lxml import etree
import requests
import time
import os
import stat

logfile = '/var/log/pydsn/dsn_dbsync.log'
app = 'dsnparser'
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


class DSNParserDB(object):

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

        if get_data:
            url = self.get_url()
            if LOCAL_DEBUG:
                self.log.info('%s :: fetching %s' % (app, url))
            try:
                response = self.http_session.get(url)
                responsetime = eut.parsedate(response.headers['date'])
                responsesec = calendar.timegm(responsetime)
                self.log.info('%s :: response date: %s -> %d (%d)' % (app, response.headers['date'], responsesec, int(responsesec / 5)))

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
            except:
                self.log.info('%s' % (traceback.format_exc()))
                self.log.info('error :: %s :: failed to get URL - %s' % (app, str(url)))
                response = 'None'
                return None
        else:
            with open(dsn_data_file, 'r') as f:
                doc = etree.fromstring(f.read())
        # doc = etree.fromstring(response.content)

        dishList = doc.xpath('/dsn/dish')
        dishes = {}
        for dish in dishList:
            dish_name, data = self.parse_dish(dish)
            dishes[dish_name] = data
        stationList = doc.xpath('/dsn/station')
        stations = {}
        for station in stationList:
            station_name, data = self.parse_station(station)
            stations[station_name] = data
        timeElem = doc.xpath('/dsn/timestamp')
        result = {
            'stations': stations,
            'dishes': dishes,
            'time': to_int(timeElem[0].text)
        }
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
            'created': dateutil.parser.parse(dish.get('created')),
            'updated': dateutil.parser.parse(dish.get('updated')),
            'targets': {},
            'up_signal': [],
            'down_signal': [],
            'flags': set()
        }
        if dish.get('isMSPA') == 'true':
            data['flags'].add('MSPA')       # Multiple Spacecraft Per Aperture
        if dish.get('isArray') == 'true':
            data['flags'].add('Array')      # Dish is arrayed
        if dish.get('isDDOR') == 'true':
            data['flags'].add('DDOR')       # Delta-Differenced One Way Range

        for target in dish.findall('target'):
            name, target_data = self.parse_target(target)
            data['targets'][name] = target_data

        for up_signal in dish.findall('upSignal'):
            data['up_signal'].append(self.parse_signal(up_signal, True))

        for down_signal in dish.findall('downSignal'):
            data['down_signal'].append(self.parse_signal(down_signal, False))

        return dish.get('name'), data

    def parse_target(self, target):
        data = {
            'spacecraft': target.get('name'),
            'spacecraft_id': int(target.get('id')),
            'up_range': float(target.get('uplegRange')),      # Up leg range, kilometers
            'down_range': float(target.get('downlegRange')),  # Down leg range, kilometers
            'rtlt': float(target.get('rtlt'))                 # Round-trip light time, in seconds
        }
        return target.get('name'), data

    def parse_signal(self, signal, isUp):
        data = {
            'frequency': to_decimal(signal.get('frequency')),   # Frequency (Hz). Always present but may be wrong if type is none
            'type': signal.get('signalType'),                   # "data", "carrier", "ranging", or "none"
            'debug': filter_value(signal.get('signalTypeDebug'), ['none', '']),
            'spacecraft': filter_value(signal.get('spacecraft'), ['']),
            'spacecraft_id': to_int(signal.get('spacecraftId')),
            'power': to_decimal(signal.get('power')),           # Power (in dBm for downlink, kW for uplink.)
            'data_rate': to_decimal(signal.get('dataRate'))     # Data rate, bits per second
        }

        # if data['debug'] is not None and data['debug'].strip() != '' and data['debug'].strip() != '-1':
        #     data['state'] = parse_debug(data['debug'], isUp)
        # else:
        #     data['state'] = None

        return data

    def fetch_config(self):
        get_data = True
        # If a local dsn_data_file exists that is less than 10 seconds old use
        # that data
        if os.path.isfile(dsn_config_file):
            file_age = file_age_in_seconds(dsn_config_file)
            if file_age < 120:
                get_data = False
                self.log.info('%s :: using local config xml file - %s seconds old' % (app, str(file_age)))

        if get_data:
            try:
                url = self.get_config_url()
                self.log.info('%s :: fetching config %s' % (app, url))
                response = self.http_session.get(url)
                responsetime = eut.parsedate(response.headers['date'])
                responsesec = calendar.timegm(responsetime)
                self.log.info('%s :: response date: %s -> %d (%d)' % (app, response.headers['date'], responsesec, int(responsesec / 5)))
                doc = etree.fromstring(response.content)
            except:
                self.log.info('error :: %s :: failed to fetch config from %s' % (app, url))
        else:
            with open(dsn_config_file, 'r') as f:
                doc = f.read()

        spacecraft = self.parse_spacecraft(doc.xpath('/config/spacecraftMap/spacecraft'))
        sites = self.parse_sites(doc.xpath('/config/sites/site'))
        return sites, spacecraft

    def parse_spacecraft(self, spacecraft):
        data = {}
        for craft in spacecraft:
            data[craft.get('name')] = craft.get('friendlyName')
        return data

    def parse_sites(self, sites):
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
                'dishes': dishes,
                'latitude': to_decimal(site.get('latitude')),
                'longitude': to_decimal(site.get('longitude'))
            }
        return data


def parse_debug(debug, isUp):
    # all of this is mostly guesswork based on watching patterns and many google searches
    flags = set()
    if isUp:
        # structure: <carrier> <encoding> <task>
        #  <carrier> is ON or OFF depending on whether a carrier is being transmitted
        #  <encoding> is 1 or 0 (occasionally -1) depending on whether data is being sent over the carrier
        #  <task> is tasks being done, so far seen: TRK (ranging), CAL (calibration), IDLE

        words = debug.split(' ')
        if words[0] == 'ON':
            flags.add('carrier')
        if words[1] == '1':
            flags.add('encoding')
        task = filter_value(words[2], '') if len(words) > 2 else None
        data = {
            'flags': flags,
            'task': task,
            'valueType': (
                'data' if 'encoding' in flags else
                'carrier' if 'carrier' in flags else
                'idle' if words[0] == 'OFF' and task == 'IDLE' else
                'task' if task and task != 'IDLE' else
                'none'
            )
        }
    else:
        # structure: <decoder1> <decoder2> <carrier> <encoding>
        #  <decoder1> shows IDLE / OUT OF LOCK / WAIT FOR LOCK / IN LOCK
        #    depending on whether a signal has been sucessflly decoded
        #  <decoder2> is only used for TURBO encoding, locks after decoder1 locks
        #  <carrier> is 1 or 0 (occasionally -1) depending on whether a carrier is heard
        #  <encoding> is the signal encoding, so far seen: MCD2, MCD3, TURBO, UNC (unconnected)
        #    MCD2=traditional standard, used on most satellites starting with Voyager
        #      Convolutional / Viterbi code, k=7, r=1/2
        #    MCD3=experimental, more difficult code for farther distances, deprecated
        #      Convolutional / Viterbi code, k=15, r=1/6
        #    TURBO=new standard for all satellites, significant improvement over MCD

        words = (debug.replace('OUT OF LOCK', 'OUT_OF_LOCK').
            replace('IN LOCK', 'IN_LOCK').
            replace('WAIT FOR LOCK', 'WAIT_FOR_LOCK').
            split(' '))
        if words[2] == '1':
            flags.add('carrier')
        decoder1 = filter_value(words[0].replace('_', ' '), '')
        decoder2 = filter_value(words[1].replace('_', ' '), '')
        data = {
            'flags': flags,
            'decoder1': decoder1,
            'decoder2': decoder2,
            'encoding': filter_value(words[3], ''),
            'valueType': (
                'data' if decoder1 == 'IN LOCK' and decoder2 in ('IN LOCK', 'OFF') else
                'carrier' if decoder1 == 'IDLE' and 'carrier' in flags else
                'carrier+' if 'carrier' in flags else
                'idle' if decoder1 == 'IDLE' else
                'idle+' if decoder1 else
                'none'
            )
        }
    return data

if __name__ == '__main__':
    parser_db = DSNParserDB()
    from pprint import pprint
    pprint(parser_db.fetch_data())
