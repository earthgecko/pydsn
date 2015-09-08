# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
import calendar
import ConfigParser
from dbmodel import *
import paste.httpheaders
from lxml.builder import E
import sdxf2
import urlparse

def application(environ, start_response):
	if environ['REQUEST_METHOD'] != 'GET':
		start_response('405 Method Not Allowed', {'Content-Length':0})
		return ['']
	
	query = urlparse.parse_qs(environ.get('QUERY_STRING',''))
	file = query.get('file', '')
	if file == 'config':
		return fetch_config(environ, start_response, query)
	elif file == 'status':
		return fetch_status(environ, start_response, query)
	else:
		start_response('400 Bad Request', {'Content-Length':0})
		return ['']

def pick_if_one(arr):
	if not(arr and isinstance(arr, (list, tuple))) or len(arr) > 1:
		return arr
	elif len(arr) == 0:
		return None
	val = arr[0]
	if val == '':
		return None
	return val

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
	with Using(db, [ConfigSite, ConfigDish, ConfigSpacecraft, ExtDish, ExtSpacecraft]):
		sites = []
		for site in ConfigSite.select():
			sites.append(site)
		dishes = {}
		for dish in (ConfigDish.select(
					ConfigDish.configsiteid, ConfigDish.id, ConfigDish.name,
					ConfigDish.friendlyname.alias('configdesc'), ConfigDish.type.alias('configtype'),
					ExtDish.descr, ExtDish.friendlyname, ExtDish.latitude, ExtDish.longitude,
					ExtDish.created)
				.join(ExtDish, join_type=JOIN.LEFT_OUTER, on=(ConfigDish.name==ExtDish.name))
				.dict()):
			if not(dish.configsiteid in dishes):
				dishes[dish['configsiteid']] = []
			dishes[dish['configsiteid']].append(dish)
		crafts = []
		for craft in (ConfigSpacecraft.select(
					ConfigSpacecraft.name, ConfigSpacecraft.encoding,
					ConfigSpacecraft.friendlyname.alias('configdesc'),
					ExtSpacecraft.agency, ExtSpacecraft.constellation, ExtSpacecraft.friendlyname,
					ExtSpacecraft.launch, ExtSpacecraft.location, ExtSpacecraft.status, ExtSpacecraft.url)
				.join(ExtSpacecraft, join_type=JOIN.LEFT_OUTER, on=(ConfigSpacecraft.name==ExtSpacecraft.name))
				.where(ConfigSpacecraft.flags=='')
				.dict()):
			crafts.append(craft)
	
	if format == 'sdxf2':
		sitesOut = []
		for site in sites:
			dishesOut = []
			if site.id in dishes:
				myDishes = dishes[site.id]
				for dish in myDishes:
					dishesOut.append({
						'ID': dish['id'],
						'name': dish['name'],
						'configFriendly': dish['configdesc'],
						'configType': dish['type'],
						'extDescr': dish['descr'],
						'extFriendly': dish['friendlyname'],
						'latitude': dish['latitude'],
						'longitude': dish['longitude'],
						'created': dish['created']
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
				'name': craft['name'],
				'encoding': craft['encoding'],
				'configFriendly': craft['configdesc'],
				'agency': craft['agency'],
				'constellation': craft['constellation'],
				'extFriendly': craft['friendlyname'],
				'launch': calendar.timegm(craft['launch'].utctimetuple()) if craft['launch'] else None,
				'location': craft['location'],
				'status': craft['status'],
				'url': craft['url']
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
						'ID': dish['id'],
						'name': dish['name'],
						'configFriendly': dish['configdesc'],
						'configType': dish['type'],
						'extDescr': dish['descr'],
						'extFriendly': dish['friendlyname'],
						'latitude': dish['latitude'],
						'longitude': dish['longitude'],
						'created': dish['created']
					}))
		craftOut = E.spacecraftMap()
		for craft in crafts:
			craftOut.append(E.spacecraft({
				'name': craft['name'],
				'encoding': craft['encoding'],
				'configFriendly': craft['configdesc'],
				'agency': craft['agency'],
				'constellation': craft['constellation'],
				'extFriendly': craft['friendlyname'],
				'launch': calendar.timegm(craft['launch'].utctimetuple()) if craft['launch'] else None,
				'location': craft['location'],
				'status': craft['status'],
				'url': craft['url']
			}))
		configOut = E.config(sitesOut, configOut).toString().encode('utf-8')
		start_response('200 Ok', {'Content-Type': 'text/xml; charset=utf-8'})
		return [configOut]

def fetch_status(environ, start_response, query):
	db = get_database()
	
	etag = httpheaders.get_header('If-None-Match')(environ)
	if etag and get_status_etag(db) == etag:
		start_response('305 Not Modified', {'Content-Length':0})
		return ['']
	
	format = query.get('format', '')
	with Using(db, [ConfigSite, ConfigDish, ConfigSpacecraft, ConfigState, DataDish, DataEvent, DataSignal]):
		configSites = {}
		for site in ConfigSite.select():
			configSites[site.id] = site
		configDishes = {}
		for dish in ConfigDish.select():
			configDishes[dish.id] = dish
		configCrafts = {}
		for craft in ConfigSpacecraft.select():
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
						.limit(1).scalar())
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
					state = configStates.get(signal.stateid, None)
					if craft and state:
						signalOut.append({
							'craft': craft.name,
							'flags': pick_if_one(signal.flags.split(',')),
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
					'name': configDish.name,
					'flags': pick_if_one(dish.flags.split(',')),
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
					'flags': pick_if_one(state.flags.split(',')),
					'task': state.task,
					'class': state.valuetype
				})
		
		with Using(db, [DataEvent]):
			maxTime = DataEvent.select(DataEvent.time).where(DataEvent.id == thisEvent).limit(1).scalar()
		statusOut = sdxf2.encode({'time':maxTime, 'dishes':dishOut, 'state':stateOut})
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
					'name': configDish.name,
					'flags': dish.flags if state.flags != '' else None
				})
				dishOut.append(dishOut)
				
				for signal in datasignals[dish.configdishid]:
					craft = configCrafts.get(signal.configspacecraftid, None)
					state = configStates.get(signal.stateid, None)
					if craft and state:
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
		
		with Using(db, [DataEvent]):
			maxTime = DataEvent.select(DataEvent.time).where(DataEvent.id == thisEvent).limit(1).scalar()
		stateOut = E.status({'time':maxTime}, dishesOut, stateOut).toString().encode('utf-8')
		start_response('200 Ok', {
			'Content-type': 'text/xml',
			'ETag': 'W/"' + unicode(thisEvent) + '"'
		})
		return [result]

def get_status_etag(db):
	with Using(db, [DataDish, DataEvent, DataSignal]):
		DishEvent = DataEvent.alias()
		SignalEvent = DataEvent.alias()
		maxTime = (DataDish.select(fn.greatest(fn.max(DishEvent.time), fn.max(SignalEvent.time)))
			.join(DishEvent, on=(DataDish.eventid==DishEvent.id))
			.join(DataSignal, on=(DataDish.id==DataSignal.configdishid))
			.join(SignalEvent, on=(DataSignal.eventid==SignalEvent.id))
			.scalar())
		maxId = DataEvent.select(DataEvent.id).where(DataEvent.time == maxTime).limit(1).scalar()
	ourEtag = 'W/"' + unicode(maxId) + '"'
	return ourEtag
