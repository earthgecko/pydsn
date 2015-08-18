# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
import ConfigParser
from dbmodel import *
import calendar
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
		self.targetHist = None
		self.last_time = 0
	
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
		if not self.existingSites:
			with Using(self.db, [ConfigSite]):
				self.existingSites = {}
				for site in ConfigSite.select():
					self.existingSites[site.name] = site
		
		if not self.existingStates:
			with Using(self.db, [ConfigState]):
				self.existingStates = {}
				for state in ConfigState.select():
					self.existingStates[state.name] = state
		
		if not self.existingDishes:
			with Using(self.db, [ConfigDish]):
				self.existingDishes = {}
				for dish in ConfigDish.select():
					self.existingDishes[dish.name] = dish
		
		if not self.spacecraftByName:
			with Using(self.db, [ConfigSpacecraft]):
				self.spacecraftById = {}
				self.spacecraftByName = {}
				for spacecraft in ConfigSpacecraft.select():
					self.spacecraftByName[spacecraft.name.lower()] = spacecraft
					if spacecraft.lastid:
						self.spacecraftById[spacecraft.lastid] = spacecraft
	
	def punch_data(self, data):
		time = data['time']
		self.log.info('Received data for time %d' % ((int)(time/5000)))
		self.load_ref()
		#self.log.info('ref loaded')
		if time == self.last_time:
			return False
		self.last_time = time
		with self.db.atomic():
			with Using(self.db, [DataEvent]):
				if DataEvent.select(DataEvent.time).where(DataEvent.time == time).exists():
					return False
				event = DataEvent.create(time=time)
			#self.log.info('stations loaded')
			self.punch_dishes(event.id, data['dishes'])
		return True
	
	def punch_dishes(self, eventid, dishes):
		with Using(self.db, [ConfigSpacecraft, ConfigState, DataDish, DataTarget, DataSignal]):
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
				created = dishData['created']
				updated = dishData['updated']
				created_time = calendar.timegm(created.utctimetuple())*1000 + created.microsecond / 1000
				updated_time = calendar.timegm(updated.utctimetuple())*1000 + updated.microsecond / 1000
				
				targets = {}
				if not self.targetHist:
					self.targetHist = {}
				if not(dish.id in self.targetHist):
					self.targetHist[dish.id] = {}
				targetHist = self.targetHist[dish.id]
				
				self.punch_targets(eventid, dish, dishData['targets'], targetOut, targetHist)
				self.punch_signals(eventid, dish, dishData['down_signal'], False, signalOut, targets)
				self.punch_signals(eventid, dish, dishData['up_signal'], True, signalOut, targets)
				
				targetList = targets.keys()
				dishOut.append({
					'configdishid': dish.id,
					'eventid': eventid,
					'azimuthangle': dishData['azimuth_angle'],
					'elevationangle': dishData['elevation_angle'],
					'createdtime': created_time,
					'updatedtimediff': updated_time - created_time,
					'windspeed': dishData['wind_speed'],
					'flags': flags,
					'targetspacecraft1': targetList[0] if len(targetList) > 0 else None,
					'targetspacecraft2': targetList[1] if len(targetList) > 1 else None,
					'targetspacecraft3': targetList[2] if len(targetList) > 2 else None
				})
			
			if len(dishOut) > 0:
				cmd = DataDish.insert_many(dishOut)
				cmd.execute()
			if len(targetOut) > 0:
				cmd = DataTarget.insert_many(targetOut)
				cmd.execute()
			if len(signalOut) > 0:
				cmd = DataSignal.insert_many(signalOut)
				cmd.execute()
	
	def punch_targets(self, eventid, dish, targets, targetOut, targetHist):
		for targetName in targets:
			targetData = targets[targetName]
			spacecraft = self.spacecraftById.get(targetData['id'], None)
			if spacecraft and spacecraft.name.lower() != targetName.lower():
				spacecraft = None
			if not spacecraft:
				spacecraft = self.spacecraftByName.get(targetName.lower(), None)
				if not spacecraft:
					return
			if targetData['down_range'] != -1 or targetData['up_range'] != -1 or targetData['rtlt'] != -1:
				if spacecraft.id in targetHist:
					histEntry = targetHist[spacecraft.id]
				else:
					histEntry = (DataTarget.select().where(
							DataTarget.configdishid==dish.id and DataTarget.configspacecraftid==spacecraft.id
						).order_by(DataTarget.eventid.desc()).limit(1).dicts().first())
					if histEntry:
						targetHist[spacecraft.id] = histEntry
				if (not histEntry or histEntry['downlegrange'] != targetData['down_range'] or 
						histEntry['uplegrange'] != targetData['up_range'] or
						histEntry['rtlt'] != targetData['rtlt']):
					newTarget = {
						'configdishid': dish.id,
						'eventid': eventid,
						'configspacecraftid': spacecraft.id,
						'downlegrange': targetData['down_range'],
						'uplegrange': targetData['up_range'],
						'rtlt': targetData['rtlt']
					}
					targetOut.append(newTarget)
					targetHist[spacecraft.id] = newTarget
			if self.spacecraftById.get(targetData['id'], None) != spacecraft:
				spacecraft.lastid = targetData['id']
				spacecraft.save()
				self.spacecraftById[targetData['id']] = spacecraft
	
	def punch_signals(self, eventid, dish, signals, isUp, signalOut, targets):
		for signalData in signals:
			if not signalData['debug']:
				continue
			if signalData['spacecraft_id'] is None:
				spacecraftid = None
			else:
				spacecraft = self.spacecraftById.get(signalData['spacecraft_id'], None)
				if spacecraft:
					spacecraftid = spacecraft.id
					targets[spacecraftid] = True
				else:
					spacecraftid = 0
					targets[0] = True
			
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
			
			if not(state.valuetype in ('none','idle')):
				newRecord = {
					'configdishid': dish.id,
					'eventid': eventid,
					'configspacecraftid': spacecraftid,
					'updown': 'up' if isUp else 'down',
					'datarate': signalData['data_rate'],
					'frequency': signalData['frequency'],
					'power': signalData['power'],
					'signaltype': signalData['type'],
					'stateid': stateid
				}
				signalOut.append(newRecord)

if __name__ == '__main__':
	import dsn
	logging.basicConfig(level=logging.INFO)
	dsn = dsn.DSN()
	sync = DBSync()
	dsn.data_callback = sync.punch_data
	dsn.config_callback = sync.sync_config
	dsn.run()
