# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
from time import sleep
import logging
from datetime import datetime, timedelta
from requests.exceptions import ConnectionError
from lxml.etree import LxmlError
from dsnparser import DSNParser

class DSN(object):
	def __init__(self):
		self.log = logging.getLogger(__name__)
		self.parser = DSNParser()
		self.last_config_update = None
		self.status_update_interval = 5  # Seconds
		self.config_update_interval = 600  # Seconds
		self.data = None
		self.config_callback = None
		self.data_callback = None    # Called for every new data update
	
	def update(self):
		try:
			now = datetime.now()
			if (self.last_config_update is None or 
					self.last_config_update < now - timedelta(minutes=self.config_update_interval)):
				self.sites, self.spacecraft = self.parser.fetch_config()
				self.last_config_update = now
				if self.config_callback:
					self.config_callback(self.sites, self.spacecraft)
			new_data = self.parser.fetch_data()
		except ConnectionError, e:
			self.log.warn("Unable to fetch data from DSN: %s" % e)
			return
		except LxmlError, e:
			self.log.warn("Unable to parse data: %s", e)
			return
		
		if self.data_callback:
			self.data_callback(new_data)
	
	def run(self):
		while True:
			self.update()
			sleep(self.status_update_interval)
