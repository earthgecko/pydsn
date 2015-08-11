# coding=utf-8
import ConfigParser
import dbmodel
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
	
	def sync_sites(self, sites):
		with Using(self.db, [ConfigSite, ConfigDish]):
			for siteName in sites:
				siteData = sites[siteName]
				try:
					site = ConfigSite.get(ConfigSite.name == siteName)
					if (site.friendlyname != siteData['friendly_name'] or
							site.latitude != siteData['latitude'] or
							site.longitude != siteData['longitude']):
						self.log.debug("Updating config: site %s" % siteName)
						cmd = (ConfigSite.update(
								friendlyname=siteData['friendly_name'],
								latitude=siteData['latitude'],
								longitude=siteData['longitude'])
							.where(ConfigSite.id == site.id))
						cmd.execute()
				except ConfigSite.DoesNotExist:
					self.log.debug("Creating config: site %s" % siteName)
					cmd = ConfigSite.create(
						name=siteName,
						friendlyname=siteData['friendly_name'],
						latitude=siteData['latitude'],
						longitude=siteData['longitude'])
					cmd.execute()
					site = ConfigSite.get(ConfigSite.name == siteName)
				
				for dishName in siteData:
					dishData = siteData[dishName]
					try:
						dish = ConfigDish.get((ConfigDish.name == dishName) or (ConfigDish.configsiteid == site.id))
						if (dish.friendlyname != dishData['friendly_name'] or
								site.type != dishData['type']):
							self.log.debug("Updating config: dish %s" % dishName)
							cmd = (ConfigDish.update(
									friendlyname=dishData['friendly_name'],
									type=dishData['type'])
								.where(ConfigDish.id == dish.id))
							cmd.execute()
					except ConfigDish.DoesNotExist:
						self.log.debug("Creating config: dish %s" % dishName)
						cmd = ConfigDish.create(
							name=dishName,
							friendlyname=dishData['friendly_name'],
							type=dishData['type'])
						cmd.execute()
	
	def sync_spacecraft(self, spacecrafts):
		with Using(self.db, [ConfigSpacecraft]):
			for spacecraftName in spacecrafts:
				spacecraftDescr = spacecrafts[spacecraftName]
				try:
					spacecraft = ConfigSpacecraft.get(ConfigSpacecraft.name == spacecraftName)
					if site.friendlyname != spacecraftDescr:
						self.log.debug("Updating config: spacecraft %s" % spacecraftName)
						cmd = (ConfigSpacecraft.update(friendlyname=spacecraftDescr)
							.where(ConfigSpacecraft.id == spacecraft.id))
						cmd.execute()
				except ConfigSpacecraft.DoesNotExist:
					self.log.debug("Creating config: spacecraft %s" % spacecraftName)
					cmd = ConfigSpacecraft.create(
						name=spacecraftName,
						friendlyname=spacecraftDescr)
					cmd.execute()
	
	def punch_data(self, data):
		time = data['time']
		self.punch_stations(time, data['stations'])
		self.punch_dishes(time, data['dishes'])
	
	def punch_stations(self, time, stations):
		with Using(self.db, [ConfigSite, DataSite]):
			for stationName in stations:
				stationData = stations[stationName]
				site = ConfigSite.get(ConfigSite.name == stationName)
				cmd = DataSite.create(
					configsiteid=site.id,
					time=time,
					timeutc=stationData['time_utc'],
					timezoneoffset=stationData['time_zone_offset'])
				cmd.execute()
	
	def punch_dishes(self, time, dishes):
		with Using(self.db, [ConfigDish, DataDish]):
			for dishName in dishes:
				dishData = dishes[dishName]
				dish = ConfigDish.get(ConfigDish.name == dishName)
				flags = ''
				for flag in dishData['flags']:
					if flags != '':
						flags += ','
					flags += flag
				cmd = DataDish.create(
					configdishid=dish.id,
					time=time,
					azimuthangle=dishData['azimuth_angle'],
					elevationangle=dishData['elevation_angle'],
					created=dishData['created'],
					updated=dishData['updated'],
					windspeed=dishData['wind_speed'],
					flags=flags)
				cmd.execute()
				
				targetMap = self.punch_targets(time, dish, dishData['targets'])
				self.punch_signals(time, dish, targetMap, dishData['down_signal'], false)
				self.punch_signals(time, dish, targetMap, dishData['up_signal'], true)
	
	def punch_targets(self, time, dish, targets):
		with Using(self.db, [ConfigSpacecraft, DataTarget]):
			targetMap = {}
			for targetName in targets:
				targetData = targets[targetName]
				spacecraft = ConfigSpacecraft.get(ConfigSpacecraft.name == targetName)
				targetMap[targetData['id']] = spacecraft.id
				cmd = DataTarget.create(
					configdishid=dish.id,
					time=time,
					configspacecraftid=spacecraft.id,
					downlegrange=targetData['down_range'],
					uplegrange=targetData['up_range'],
					rtlt=targetData['rtlt'])
				cmd.execute()
				if spacecraft.lastid != targetData['id']:
					cmd = (ConfigSpacecraft.update(lastid=targetData['id'])
						.where(ConfigSpacecraft.id == spacecraft.id))
					cmd.execute()
			return targetMap
	
	def punch_signals(self, time, dish, targetMap, signals, isUp):
		with Using(self.db, [DataSignal]):
			seq = 1
			for signalData in signals:
				if signalData['spacecraft_id'] is None:
					spacecraftId = None
				else:
					spacecraftId = targetMap[signalData['spacecraft_id']]
				
				flags = ''
				state = signalData['state']
				if state is not None:
					if state['carrier'] == True:
						if flags != '':
							flags += ',';
						flags += 'carrier'
					if state['tracking'] == True:
						if flags != '':
							flags += ',';
						flags += 'tracking'
					if state['encoder'] == 'ON':
						if flags != '':
							flags += ',';
						flags += 'encoding'
				
				cmd = DataSignal.create(
					configdishid=dish.id,
					time=time,
					seq=seq,
					configspacecraftid=spacecraftId,
					updown=isUp if isUp else 'down',
					flags=flags,
					datarate=signalData['data_rate'],
					frequency=signalData['frequency'],
					power=signalData['power'],
					signaltype=signalData['type'],
					signaltypedebug=state,
					decoder1 = state['decoder1'] if state is not None else None,
					decoder2 = state['decoder2'] if state is not None else None,
					encoding = state['encoding'] if state is not None else None)
				cmd.execute()
				seq += 1
