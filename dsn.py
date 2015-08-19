# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
import time
import logging
from requests.exceptions import ConnectionError
from lxml.etree import LxmlError
from dsnparser import DSNParser

class DSN(object):
	def __init__(self):
		self.log = logging.getLogger(__name__)
		self.parser = DSNParser()
		self.next_config_update = 0
		self.next_data_update = 0
		self.status_update_interval = 5  # Seconds
		self.config_update_interval = 600  # Seconds
		self.config_callback = None
		self.data_callback = None    # Called for every new data update
	
	def update(self):
		try:
			now = time.time()
			if self.next_config_update <= now:
				self.next_config_update = now + self.config_update_interval
				self.sites, self.spacecraft = self.parser.fetch_config()
				if self.config_callback:
					self.config_callback(self.sites, self.spacecraft)
					self.log.info('Config processing complete')
			
			now = time.time()
			if self.next_data_update <= now:
				self.next_data_update = (int)(now / self.status_update_interval + 1) * self.status_update_interval
				new_data = self.parser.fetch_data()
				if self.data_callback:
					if not self.data_callback(new_data):
						self.log.info('Status processing rejected')
					else:
						self.log.info('Status processing complete')
		
		except ConnectionError, e:
			self.log.warn("Unable to fetch data from DSN: %s" % e)
			return
		except LxmlError, e:
			self.log.warn("Unable to parse data: %s", e)
			return
		
	def run(self):
		while True:
			self.update()
			time.sleep(1)
