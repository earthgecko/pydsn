# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
import ConfigParser
from dbmodel import *
import logging
from peewee import Using
from playhouse.pool import PooledMySQLDatabase

class DBSync(object):
	def __init__(self):
		self.log = logging.getLogger(__name__)
		self.config = ConfigParser.ConfigParser()
		self.config.read('dsn.conf')
		#self.db = MySQLDatabase(self.config.get('db', 'database'), **{
		self.db = PooledMySQLDatabase(self.config.get('db', 'database'),
			host = self.config.get('db', 'host'),
			user = self.config.get('db', 'user'),
			password = self.config.get('db', 'password'),
			stale_timeout = 300 # 5 minutes
		)
		self.existingSites = None
		self.existingStates = None
		self.existingDishes = None
		self.spacecraftById = None
		self.spacecraftByName = None
	
	def sync_config(self, sites, spacecrafts):
		self.flush_ref()
		self.sync_sites(sites)
		self.sync_spacecraft(spacecrafts)
	
	def sync_sites(self, sites):
		with Using(self.db, [ConfigSite, ConfigDish]):
			with self.db.atomic():
				existingSites = {}
				for site in ConfigSite.select():
					existingSites[site.name] = site
				existingDishes = {}
				for dish in ConfigDish.select():
					existingDishes[dish.name] = dish
				for siteName in sites:
					siteData = sites[siteName]
					site = existingSites.get(siteName, None)
					if site:
						if (site.friendlyname != siteData['friendly_name'] or
								site.latitude != siteData['latitude'] or
								site.longitude != siteData['longitude']):
							self.log.info("Updating config: site %s" % siteName)
							cmd = (ConfigSite.update(
									friendlyname=siteData['friendly_name'],
									latitude=siteData['latitude'],
									longitude=siteData['longitude'])
								.where(ConfigSite.id == site.id))
							cmd.execute()
					else:
						self.log.info("Creating config: site %s" % siteName)
						site = ConfigSite.create(
							name=siteName,
							friendlyname=siteData['friendly_name'],
							latitude=siteData['latitude'],
							longitude=siteData['longitude'])
					
					for dishName in siteData['dishes']:
						dishData = siteData['dishes'][dishName]
						dish = existingDishes.get(dishName, None)
						if dish:
							if (dish.friendlyname != dishData['friendly_name'] or
									dish.type != dishData['type']):
								self.log.info("Updating config: dish %s" % dishName)
								cmd = (ConfigDish.update(
										friendlyname=dishData['friendly_name'],
										type=dishData['type'])
									.where(ConfigDish.id == dish.id))
								cmd.execute()
						else:
							self.log.info("Creating config: dish %s" % dishName)
							ConfigDish.create(
								name=dishName,
								configsiteid=site.id,
								friendlyname=dishData['friendly_name'],
								type=dishData['type'])
	
	def sync_spacecraft(self, spacecrafts):
		with Using(self.db, [ConfigSpacecraft]):
			with self.db.atomic():
				existingSpacecraft = {}
				for spacecraft in ConfigSpacecraft.select():
					existingSpacecraft[spacecraft.name] = spacecraft
				for spacecraftName in spacecrafts:
					spacecraftDescr = spacecrafts[spacecraftName]
					spacecraft = existingSpacecraft.get(spacecraftName, None)
					if spacecraft:
						if spacecraft.friendlyname != spacecraftDescr:
							self.log.info("Updating config: spacecraft %s" % spacecraftName)
							cmd = (ConfigSpacecraft.update(friendlyname=spacecraftDescr)
								.where(ConfigSpacecraft.id == spacecraft.id))
							cmd.execute()
					else:
						self.log.info("Creating config: spacecraft %s" % spacecraftName)
						ConfigSpacecraft.create(
							name=spacecraftName,
							friendlyname=spacecraftDescr)
	
	def flush_ref(self):
		self.existingSites = None
		self.existingStates = None
		self.existingDishes = None
		self.spacecraftById = None
		self.spacecraftByName = None
	
	def load_ref(self):
		with Using(self.db, [ConfigSite, ConfigState, ConfigDish, ConfigSpacecraft]):
			if not self.existingSites:
				self.existingSites = {}
				for site in ConfigSite.select():
					self.existingSites[site.name] = site
			
			if not self.existingStates:
				self.existingStates = {}
				for state in ConfigState.select():
					self.existingStates[state.name] = state
			
			if not self.existingDishes:
				self.existingDishes = {}
				for dish in ConfigDish.select():
					self.existingDishes[dish.name] = dish
			
			if not self.spacecraftByName:
				self.spacecraftById = {}
				self.spacecraftByName = {}
				for spacecraft in ConfigSpacecraft.select():
					self.spacecraftByName[spacecraft.name.lower()] = spacecraft
					if spacecraft.lastid:
						self.spacecraftById[spacecraft.lastid] = spacecraft

	
	def punch_data(self, data):
		time = data['time']
		self.load_ref()
		#self.log.info('ref loaded')
		with Using(self.db, [DataSite]):
			if DataSite.select(DataSite.time).where(DataSite.time == time).exists():
				return False
			self.punch_stations(time, data['stations'])
		#self.log.info('stations loaded')
		self.punch_dishes(time, data['dishes'])
		return True
	
	def punch_stations(self, time, stations):
		with self.db.atomic():
			dataSiteRows = []
			for stationName in stations:
				stationData = stations[stationName]
				site = self.existingSites[stationName]
				dataSiteRows.append({
					'configsiteid': site.id,
					'time': time,
					'timeutc': stationData['time_utc'],
					'timezoneoffset': stationData['time_zone_offset']})
			if len(dataSiteRows) > 0:
				cmd = DataSite.insert_many(dataSiteRows)
				cmd.execute()
	
	def punch_dishes(self, time, dishes):
		with Using(self.db, [ConfigSpacecraft, ConfigState, DataDish, DataTarget, DataSignal]):
			with self.db.atomic():
				dishOut = []
				targetOut = []
				signalOut = []
				for dishName in dishes:
					dishData = dishes[dishName]
					dish = self.existingDishes[dishName]
					flags = ''
					for flag in dishData['flags']:
						if flags != '':
							flags += ','
						flags += flag
					dishOut.append({
						'configdishid': dish.id,
						'time': time,
						'azimuthangle': dishData['azimuth_angle'],
						'elevationangle': dishData['elevation_angle'],
						'created': self.db.truncate_date('second', dishData['created']),
						'updated': self.db.truncate_date('second', dishData['updated']),
						'windspeed': dishData['wind_speed'],
						'flags': flags
					})
					self.punch_targets(time, dish, dishData['targets'], targetOut)
					self.punch_signals(time, dish, dishData['down_signal'], False, signalOut)
					self.punch_signals(time, dish, dishData['up_signal'], True, signalOut)
				
				if len(dishOut) > 0:
					cmd = DataDish.insert_many(dishOut)
					cmd.execute()
				if len(targetOut) > 0:
					cmd = DataTarget.insert_many(targetOut)
					cmd.execute()
				if len(signalOut) > 0:
					cmd = DataSignal.insert_many(signalOut)
					cmd.execute()
	
	def punch_targets(self, time, dish, targets, targetOut):
		for targetName in targets:
			targetData = targets[targetName]
			spacecraft = self.spacecraftById.get(targetData['id'], None)
			if spacecraft and spacecraft.name.lower() != targetName.lower():
				spacecraft = None
			if not spacecraft:
				spacecraft = self.spacecraftByName.get(targetName.lower(), None)
			if spacecraft:
				if targetData['down_range'] != -1 or targetData['up_range'] != -1 or targetData['rtlt'] != -1:
					targetOut.append({
						'configdishid': dish.id,
						'time': time,
						'configspacecraftid': spacecraft.id,
						'downlegrange': targetData['down_range'],
						'uplegrange': targetData['up_range'],
						'rtlt': targetData['rtlt']
					})
				if self.spacecraftById.get(targetData['id'], None) != spacecraft:
					spacecraft.lastid = targetData['id']
					spacecraft.save()
					self.spacecraftById[targetData['id']] = spacecraft
	
	def punch_signals(self, time, dish, signals, isUp, signalOut):
		seq = 1
		for signalData in signals:
			if not signalData['debug']:
				continue
			isTesting = False
			if signalData['spacecraft_id'] is None:
				spacecraftid = None
			else:
				spacecraft = self.spacecraftById.get(signalData['spacecraft_id'], None)
				if spacecraft:
					spacecraftid = spacecraft.id
				else:
					spacecraftid = None
					isTesting = True
			
			stateid = None
			if signalData['debug']:
				state = self.existingStates.get(signalData['debug'], None)
				if not state:
					state = ConfigState.create(
						name = signalData['debug'],
						updown = 'UP' if isUp else 'down',
						signaltype = signalData['type']
					)
					self.existingStates[state.name] = state
				stateid = state.id
			
			newRecord = {
				'configdishid': dish.id,
				'time': time,
				'seq': seq,
				'configspacecraftid': spacecraftid,
				'updown': 'UP' if isUp else 'down',
				'datarate': signalData['data_rate'],
				'frequency': signalData['frequency'],
				'power': signalData['power'],
				'signaltype': signalData['type'],
				'stateid': stateid,
				'flags': 'testing' if isTesting else ''
			}
			seq += 1
			
			signalOut.append(newRecord)

if __name__ == '__main__':
	import dsn
	logging.basicConfig(level=logging.INFO)
	dsn = dsn.DSN()
	sync = DBSync()
	dsn.data_callback = sync.punch_data
	dsn.config_callback = sync.sync_config
	dsn.run()
