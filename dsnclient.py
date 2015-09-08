# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
import ConfigParser
from dbmodel import *
from lxml.builder import E
import sdxf2
import urlparse

def application(environ, start_response):
	if environ['REQUEST_METHOD'] != 'GET':
		start_response('405 Method Not Allowed', {'Content-Length':0})
		return ('')
	
	query = urlparse.parse_qs(environ.get('QUERY_STRING',''))
	file = query.get('file', '')
	if file == 'config':
		return fetch_config(environ, start_response, query)
	elif file == 'status':
		return fetch_status(environ, start_response, query)
	else:
		start_response('400 Bad Request', {'Content-Length':0})
		return ('')
	#format = query.get('format', '')
	#etag = environ.get('ETag', '')

def get_database():
	config = ConfigParser.ConfigParser()
	config.read('dsn.conf')
	#db = MySQLDatabase(self.config.get('db', 'database'), **{
	db = PooledMySQLDatabase(self.config.get('db', 'database'),
		host = self.config.get('db', 'host'),
		user = self.config.get('db', 'user'),
		password = self.config.get('db', 'password'),
		stale_timeout = 300 # 5 minutes
	)
	return db

def fetch_config(environ, start_response, query):
	db = get_database()
	format = query.get('format', '')
	with Using(db, [ConfigSite, ConfigDish, ConfigSpacecraft]):
		sites = []
		for site in ConfigSite.select():
			sites.append(site)
		dishes = {}
		for dish in ConfigDish.select():
			if not(dish.configsiteid in dishes):
				dishes[dish.configsiteid] = []
			dishes[dish.configsiteid].append(dish)
		crafts = []
		for craft in ConfigSpacecraft.select().where(ConfigSpacecraft.flags==''):
			crafts.append(craft)
	
	if format == 'sdxf2':
		sitesOut = []
		for site in sites:
			dishesOut = []
			if site.id in dishes:
				myDishes = dishes[site.id]
				for dish in myDishes:
					dishesOut.append({
						'friendlyName': dish.friendlyname,
						'name': dish.name,
						'type': dish.type
					})
			sitesOut.append({
				'friendlyName': site.friendlyname,
				'latitude': site.latitude,
				'longitude': site.longitude,
				'name': site.name,
				'timeZoneOffset': site.timezoneoffset,
				'dishes': dishesOut
			})
		craftOut = []
		for craft in crafts:
			craftOut.append({
				'encoding': craft.encoding,
				'friendlyName': craft.friendlyname,
				'name': craft.name
			})
		configOut = sdxf2.encode({'sites':sitesOut,'spacecraft':craftOut})
		start_response('200 Ok', {'Content-Type': 'application/x-sdxf2'})
		return [configOut]

	else: # default to XML
		sitesOut = E.sites()
		for site in sites:
			siteOut = E.site({
				'friendlyName': site.friendlyname,
				'latitude': site.latitude,
				'longitude': site.longitude,
				'name': site.name,
				'timeZoneOffset': site.timezoneoffset,
			})
			sitesOut.append(siteOut)
			if site.id in dishes:
				myDishes = dishes[site.id]
				for dish in myDishes:
					siteOut.append(E.dish({
						'friendlyName': dish.friendlyname,
						'name': dish.name,
						'type': dish.type
					}))
		craftOut = E.spacecraftMap()
		for craft in crafts:
			craftOut.append(E.spacecraft({
				'encoding': craft.encoding,
				'friendlyName': craft.friendlyname,
				'name': craft.name
			}))
		configOut = E.config(sitesOut, configOut).toString().encode('utf-8')
		start_response('200 Ok', {'Content-Type': 'text/xml; charset=utf-8'})
		return [configOut]

def fetch_status(environ, start_response, query):
	db = get_database()
	format = query.get('format', '')
	with Using(db, [ConfigSite, ConfigDish, ConfigSpacecraft, ConfigState, DataDish, DataEvent, DataSignal]):
		configSites = {}
		for site in ConfigSite.select():
			configSites[site.id] = site
		configDishes = {}
		for dish in ConfigDish.select():
			configDishes[dish.id] = dish
		configCrafts = {}
		for craft in ConfigSpacecraft.select().where(ConfigSpacecraft.flags==''):
			configCrafts[craft.id] = craft
		configstates = {}
		for state in ConfigState.select():
			if not (state.valuetype in ('none','idle')):
				configstates[state.id] = state
		datadishes = []
		datasignals = {}
		for dishid in (DataDish.select(DataDish.configdishid, fn.max(DataEvent.time).alias('time'))
				.join(DataEvent, on=(DataDish.eventid==DataEvent.id))
				.group_by(DataDish.configdishid).dict()):
			for dish in (DataDish.select()
					.join(DataEvent, on=(DataDish.eventid==DataEvent.id))
					.where(DataDish.configdishid==dishid['configdishid'] & DataEvent.time==dishid['time'])):
				datadishes.push(dish)
				datasignals[dish.configdishid] = []
				
				signalEvent = (DataSignal.select(DataSignal.eventid)
						.join(DataEvent, on=(DataSignal.eventid==DataEvent.id))
						.where(DataSignal.configdishid == dish.id)
						.order_by(DataEvent.time.desc())
						.limit(1).first().scalar())
				for signal in (DataSignal.select()
						.where(DataSignal.configdishid==dish.id & DataSignal.eventid==signalEvent)):
					datasignals[dish.configdishid].push(signal)
	
	thisEvent = 0
	usedStates = {}
	
	if format == 'sdxf2':
		dishOut = []
		for dish in dishes:
			configDish = configDishes.get(dish.configdishid, None)
			if configDish:
				signalOut = []
				if thisEvent < dish.eventid:
					thisEvent = dish.eventid
				
				for signal in datasignals[dish.configdishid]:
					craft = configCrafts.get(signal.configspacecraftid, None)
					if craft:
						signalOut.append({
							'craft': craft.name,
							'flags': signal.flags.split(','),
							'state': signal.stateid,
							'upDown': signal.updown
						})
						if not(signal.stateid in usedStates):
							usedStates[signal.stateid] = True
						if thisEvent < signal.eventid:
							thisEvent = signal.eventid
				
				targetOut = []
				if dish.targetspacecraft1:
					craft = configCrafts.get(dish.targetspacecraft1, None)
					if craft:
						targetOut.append({'craft': craft.name})
				if dish.targetspacecraft2:
					craft = configCrafts.get(dish.targetspacecraft2, None)
					if craft:
						targetOut.append({'craft': craft.name})
				if dish.targetspacecraft3:
					craft = configCrafts.get(dish.targetspacecraft3, None)
					if craft:
						targetOut.append({'craft': craft.name})
				
				dishOut.append({
					'ID': dish.id,
					'name': configDish.name,
					'flags': dish.flags.split(','),
					'signals': signalOut,
					'targets': targetOut
				})
		
		stateOut = []
		for id in usedStates:
			state = configStates.get(id, None)
			if state:
				stateOut.append({
					'ID': state.id,
					'upDown': state.updown,
					'decoder1': state.decoder1,
					'decoder2': state.decoder2,
					'encoding': state.encoding,
					'flags': state.flags.split(','),
					'task': state.task,
					'class': state.valuetype
				})
		
		statusOut = sdxf2.encode({'dishes':dishOut, 'state':stateOut})
		start_response('200 Ok', {
			'Content-type': 'application/x-sdxf2',
			'ETag': 'W/"' + unicode(thisEvent) + '"'
		})
		return [statusOut]

	else: # default to XML
		dishesOut = E.dishes()
		for dish in dishes:
			configDish = configDishes.get(dish.configdishid, None)
			if configDish:
				if thisEvent < dish.eventid:
					thisEvent = dish.eventid
				
				dishOut = E.dish({
					'ID': dish.id,
					'name': configDish.name,
					'flags': dish.flags if state.flags != '' else None
				})
				dishOut.append(dishOut)
				
				for signal in datasignals[dish.configdishid]:
					craft = configCrafts.get(signal.configspacecraftid, None)
					if craft:
						dishOut.append(E.signal({
							'craft': craft.name,
							'flags': signal.flags if state.flags != '' else None,
							'state': signal.stateid,
							'upDown': signal.updown
						}))
						if not(signal.stateid in usedStates):
							usedStates[signal.stateid] = True
						if thisEvent < signal.eventid:
							thisEvent = signal.eventid
			
			if dish.targetspacecraft1:
				craft = configCrafts.get(dish.targetspacecraft1, None)
				if craft:
					dishOut.append(E.target({'craft': craft.name}))
			if dish.targetspacecraft2:
				craft = configCrafts.get(dish.targetspacecraft2, None)
				if craft:
					dishOut.append(E.target({'craft': craft.name}))
			if dish.targetspacecraft3:
				craft = configCrafts.get(dish.targetspacecraft3, None)
				if craft:
					dishOut.append(E.target({'craft': craft.name}))
		
		stateOut = E.states()
		for id in usedStates:
			state = configStates.get(id, None)
			if state:
				stateOut.append(E.state({
					'ID': state.id,
					'upDown': state.updown,
					'decoder1': state.decoder1,
					'decoder2': state.decoder2,
					'encoding': state.encoding,
					'flags': state.flags if state.flags != '' else None,
					'task': state.task,
					'class': state.valuetype
				}))
		
		stateOut = E.state(dishesOut, stateOut).toString().encode('utf-8')
		start_response('200 Ok', {
			'Content-type': 'text/xml',
			'ETag': 'W/"' + unicode(thisEvent) + '"'
		})
		return [result]
