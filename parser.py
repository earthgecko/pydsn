# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
import time
import requests
import logging
import dateutil.parser
from lxml import etree


def to_decimal(value):
	if value == '' or value == 'null':
		return None
	return float(value)

def filter_value(value, exclusions):
	if value in exclusions:
		return None
	return value

class DSNParser(object):
	
	def __init__(self):
		self.log = logging.getLogger(__name__)
		self.http_session = requests.Session()
	
	def get_url(self):
		return "http://eyes.nasa.gov/dsn/data/dsn.xml?r=%s" % (int)(time.time() / 5)
	
	def get_config_url(self):
		return "http://eyes.nasa.gov/dsn/config.xml"
	
	def fetch_data(self):
		url = self.get_url()
		self.log.debug("Fetching %s" % url)
		response = self.http_session.get(url)
		doc = etree.fromstring(response.content)
		dishes = doc.xpath('/dsn/dish')
		result = {}
		for dish in dishes:
			dish_name, data = self.parse_dish(dish)
			result[dish_name] = data
		return result
	
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
			data['flags'].add('MSPA')									# Multiple Spacecraft Per Aperture
		if dish.get('isArray') == 'true':
			data['flags'].add('Array')									# Dish is arrayed
		if dish.get('isDDOR') == 'true':
			data['flags'].add('DDOR')									# Delta-Differenced One Way Range
		
		for target in dish.findall('target'):
			name, target_data = self.parse_target(target)
			data['targets'][name] = target_data
		
		for up_signal in dish.findall('upSignal'):
			data['up_signal'].append(self.parse_signal(up_signal, True))
		
		for down_signal in dish.findall('downSignal'):
			data['down_signal'].append(self.parse_signal(down_signal, False))
		
		#if 'DSN' in data['targets']:
		#	# A target of 'DSN' seems to indicate that the dish is out of service
		#	data['targets'] = {}
		#	data['up_signal'] = []
		#	data['down_signal'] = []
		#	data['online'] = False
		#else:
		#	data['online'] = True
		
		return dish.get('name'), data
	
	def parse_target(self, target):
		data = {
			'id': int(target.get('id')),
			'up_range': float(target.get('uplegRange')),        # Up leg range, meters
			'down_range': float(target.get('downlegRange')),    # Down leg range, meters
			'rtlt': float(target.get('rtlt'))                   # Round-trip light time, in seconds
		}
		return target.get('name'), data
	
	def parse_signal(self, signal, isUp):
		#if signal.get('spacecraft') == 'DSN':
		#    # DSN is a bogus spacecraft
		#    return None
		data = {
			'type': signal.get('signalType'),                   # "data", "carrier", "ranging", or "none"
			'debug': filter_value(signal.get('signalTypeDebug'), ['none','']),
			'spacecraft': filter_value(signal.get('spacecraft'), ['']),
			'spacecraft_id': to_decimal(signal.get('spacecraftId')),
			'power': to_decimal(signal.get('power')),           # Power (in dBm for downlink, kW for uplink.)
			'data_rate': to_decimal(signal.get('dataRate'))     # Data rate, bits per second
		}
		
		if signal.get('frequency') == '' or signal.get('frequency') == 'none':
			data['frequency'] = None
		else:
			data['frequency'] = to_decimal(signal.get('frequency'))   # Frequency (Hz). Always present but may be wrong if type is none
			
		if data['spacecraft_id'] is not None:
			data['spacecraft_id'] = int(data['spacecraft_id'])
		
		if data['debug'] is not None:
			data['state'] = self.parse_debug(data['debug'], isUp)
		else:
			data['state'] = None
		
		return data
	
	def parse_debug(self, debug, isUp):
		# all of this is mostly guesswork based on watching patterns and many google searches
		if isUp:
			words = debug.split()
			data = {
				'encoder': words[0],
				'carrier': words[1] == '1',
				'tracking': len(words) > 2 and words[2] == 'TRK'
			}
		else:
			words = debug.replace('OUT OF LOCK','OUT_OF_LOCK').replace('IN LOCK','IN_LOCK').split()
			data = {
				'decoder1': words[0].replace('_', ' '),
				'decoder2': words[1].replace('_', ' '),
				'carrier': words[2] == '1',
				'encoding': words[3]
			}
		return data
	
	def fetch_config(self):
		url = self.get_config_url()
		self.log.debug("Fetching config %s" % url)
		response = self.http_session.get(url)
		doc = etree.fromstring(response.content)
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
