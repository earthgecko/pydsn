# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
import ConfigParser
from dbmodel import *
import logging
from peewee import MySQLDatabase, Using

class DBSync(object):
	def __init__(self):
		self.log = logging.getLogger(__name__)
		self.config = ConfigParser.ConfigParser()
		self.config.read('dsn.conf')
		self.db = MySQLDatabase(self.config.get('db', 'database'), **{
			'host': self.config.get('db', 'host'),
			'user': self.config.get('db', 'user'),
			'password': self.config.get('db', 'password')})
	
	def sync_config(self, sites, spacecrafts):
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
	
	def punch_data(self, data):
		time = data['time']
		self.punch_stations(time, data['stations'])
		self.punch_dishes(time, data['dishes'])
	
	def punch_stations(self, time, stations):
		with Using(self.db, [ConfigSite, DataSite]):
			with self.db.atomic():
				existingSites = {}
				for site in ConfigSite.select():
					existingSites[site.name] = site
				dataSiteRows = []
				for stationName in stations:
					stationData = stations[stationName]
					site = existingSites[stationName]
					dataSiteRows.append({
						'configsiteid': site.id,
						'time': time,
						'timeutc': stationData['time_utc'],
						'timezoneoffset': stationData['time_zone_offset']})
				if len(dataSiteRows) > 0:
					cmd = DataSite.insert_many(dataSiteRows)
					cmd.execute()
	
	def punch_dishes(self, time, dishes):
		with Using(self.db, [ConfigSpacecraft, ConfigState, ConfigDish, DataDish, DataTarget, DataSignal]):
			with self.db.atomic():
				existingStates = {}
				for state in ConfigState.select():
					existingStates[state.name] = state
				existingDishes = {}
				for dish in ConfigDish.select():
					existingDishes[dish.name] = dish
				spacecraftById = {}
				spacecraftByName = {}
				for spacecraft in ConfigSpacecraft.select():
					spacecraftByName[spacecraft.name.lower()] = spacecraft
					if spacecraft.lastid:
						spacecraftById[spacecraft.lastid] = spacecraft
				self.log.info("Reference data fetched")
				dishOut = []
				targetOut = []
				signalOut = []
				for dishName in dishes:
					dishData = dishes[dishName]
					dish = existingDishes[dishName]
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
						'created': dishData['created'].replace(microsecond=0),
						'updated': dishData['updated'].replace(microsecond=0),
						'windspeed': dishData['wind_speed'],
						'flags': flags
					})
					self.punch_targets(time, dish, dishData['targets'], spacecraftById, spacecraftByName, targetOut)
					self.punch_signals(time, dish, spacecraftById, existingStates, dishData['down_signal'], False, signalOut)
					self.punch_signals(time, dish, spacecraftById, existingStates, dishData['up_signal'], True, signalOut)
				
				if len(dishOut) > 0:
					cmd = DataDish.insert_many(dishOut)
					cmd.execute()
				if len(targetOut) > 0:
					cmd = DataTarget.insert_many(targetOut)
					cmd.execute()
				if len(signalOut) > 0:
					cmd = DataSignal.insert_many(signalOut)
					cmd.execute()
	
	def punch_targets(self, time, dish, targets, spacecraftById, spacecraftByName, targetOut):
		for targetName in targets:
			targetData = targets[targetName]
			spacecraft = spacecraftById.get(targetData['id'], None)
			if spacecraft and spacecraft.name.lower() != targetName.lower():
				spacecraft = None
			if not spacecraft:
				spacecraft = spacecraftByName.get(targetName.lower(), None)
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
				if spacecraftById.get(targetData['id'], None) != spacecraft:
					cmd = (ConfigSpacecraft.update(lastid=targetData['id'])
						.where(ConfigSpacecraft.id == spacecraft.id))
					cmd.execute()
					spacecraftById[targetData['id']] = spacecraft
	
	def punch_signals(self, time, dish, spacecraftById, existingStates, signals, isUp, signalOut):
		seq = 1
		for signalData in signals:
			if not signalData['debug']:
				continue
			isTesting = False
			if signalData['spacecraft_id'] is None:
				spacecraft = None
			else:
				spacecraft = spacecraftById.get(signalData['spacecraft_id'], None)
				if not spacecraft:
					isTesting = True
			
			stateid = None
			if signalData['debug']:
				state = existingStates.get(signalData['debug'], None)
				if not state:
					state = ConfigState.create(
						name = signalData['debug'],
						updown = 'UP' if isUp else 'down',
						signaltype = signalData['type']
					)
					existingStates[state.name] = state
				stateid = state.id
			
			newRecord = {
				'configdishid': dish.id,
				'time': time,
				'seq': seq,
				'configspacecraftid': spacecraft.id,
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
