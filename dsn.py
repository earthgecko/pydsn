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
		self.last_config_update = None
		self.last_data_update = None
		self.status_update_interval = 5  # Seconds
		self.config_update_interval = 600  # Seconds
		self.config_callback = None
		self.data_callback = None    # Called for every new data update
	
	def update(self):
		try:
			now = time.time()
			
			if (self.last_config_update is None or 
					self.last_config_update <= now - self.config_update_interval):
				self.last_config_update = now
				self.sites, self.spacecraft = self.parser.fetch_config()
				if self.config_callback:
					self.config_callback(self.sites, self.spacecraft)
					self.log.info('Config processing complete')
			
			if (self.last_data_update is None or 
					self.last_data_update <= now - self.status_update_interval):
				self.last_data_update = now
				new_data = self.parser.fetch_data()
				if self.data_callback:
					self.data_callback(new_data)
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
