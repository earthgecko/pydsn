# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
import calendar
import ConfigParser
from dbmodel import *
from dsnparser import parse_debug
import logging
from operator import itemgetter
from peewee import Using
from playhouse.pool import PooledMySQLDatabase

from pprint import pprint

logfile = '/tmp/pydsn.log'
logging.basicConfig(
    filename=logfile,
    filemode='a',
    level=logging.INFO,
    format="%(asctime)s :: %(process)s :: %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S')


class DBSync(object):
    def __init__(self):
        self.stdout_path = logfile
        self.stderr_path = logfile
        self.log = logging.getLogger(__name__)
        self.config = ConfigParser.ConfigParser()
        self.config.read('dsn.conf')
        # self.db = MySQLDatabase(self.config.get('db', 'database'), **{
        self.db = PooledMySQLDatabase(self.config.get('db', 'database'),
			host=self.config.get('db', 'host'),
            user=self.config.get('db', 'user'),
            password=self.config.get('db', 'password'),
            stale_timeout=300  # 5 minutes
        )
        self.existingSites = None
        self.existingStates = None
        self.existingDishes = None
        self.spacecraftById = None
        self.spacecraftByName = None
        self.targetHist = None
        self.dishHist = None
        self.signalHist = None
        self.detailHist = None
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
                            if (dish.configsiteid != site.id or
                                    dish.friendlyname != dishData['friendly_name'] or
                                    dish.type != dishData['type']):
                                self.log.info("Updating config: dish %s" % dishName)
                                cmd = (ConfigDish.update(
                                        configsiteid=site.id,
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
                        if spacecraft.friendlyname != spacecraftDescr or spacecraft.flags != '':
                            self.log.info("Updating config: spacecraft %s" % spacecraftName)
                            cmd = (ConfigSpacecraft.update(friendlyname=spacecraftDescr, lastid=None, flags='')
                                .where(ConfigSpacecraft.id == spacecraft.id))
                            cmd.execute()
                    else:
                        self.log.info("Creating config: spacecraft %s" % spacecraftName)
                        ConfigSpacecraft.create(name=spacecraftName, friendlyname=spacecraftDescr)

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
        this_time = data['time']
        if not this_time:
            self.log.warning('Ignoring response with no time')
            pprint(data)
            return False
        self.log.info('Received data for time %d' % ((int)(this_time / 5000)))
        self.load_ref()
        # self.log.info('ref loaded')

        is_backdated = None
        if this_time == self.last_time:
            self.log.info('Ignoring duplicate time %d' % this_time)
            return False
        elif this_time < self.last_time:
            self.log.info('Handling backdated data (%d < %d)' % (this_time, self.last_time))
            is_backdated = this_time
        else:
            self.last_time = this_time

        with self.db.atomic():

            # handle station data
            for stationName in data['stations']:
                stationData = data['stations'][stationName]
                site = self.existingSites[stationName]
                if stationData['time_zone_offset'] != site.timezoneoffset:
                    with Using(self.db, [ConfigSite]):
                        site.timezoneoffset = stationData['time_zone_offset']
                        site.save()
            # self.log.info('stations loaded')

            # create the time event
            with Using(self.db, [DataEvent]):
                if DataEvent.select(DataEvent.time).where(DataEvent.time == this_time).exists():
                    self.log.info('Ignoring previously logged time %d' % this_time)
                    return False
                event = DataEvent.create(time=this_time)

            # do everything else
            self.punch_dishes(event.id, is_backdated, data['dishes'])
        return True

    def discover_arrays(self, dishes):
        # go through the signals being specified by arrayed dishes and try to find the "primary" signal,
        # if there is one (yet)
        minorSignals = {}
        majorSignals = {}
        for dishName in dishes:
            dishData = dishes[dishName]
            if not('Array' in dishData['flags']):
                continue
            for signalData in dishData['down_signal']:
                spacecraft = self.get_spacecraft(signalData)
                state = self.get_state(signalData['debug'], False, signalData['type'])
                if state.valuetype in ('data', 'carrier+'):
                    majorSignals[spacecraft.id] = signalData
                else:
                    minorSignals[spacecraft.id] = signalData
        results = {}
        for spacecraftId in majorSignals:
            if spacecraftId in minorSignals:
                results[spacecraftId] = majorSignals[spacecraftId]
        return results

    def punch_dishes(self, eventid, is_backdated, dishes):
        with Using(self.db,[
		ConfigDish, ConfigSpacecraft, ConfigState, DataDish,
    	DataDishPos, DataTarget, DataSignal, DataSignalDet]):
            arrayedSignals = self.discover_arrays(dishes)
            dishOut = []
            targetOut = []
            signalOut = []
            for dishName in dishes:
                if not (dishName in self.existingDishes):
                    dish = ConfigDish.create(name=dishName)
                    self.existingDishes[dishName] = dish
                else:
                    dish = self.existingDishes[dishName]

                dishData = dishes[dishName]
                flags = ','.join(sorted(dishData['flags']))
                created = dishData['created']
                self.log.info('created - %s' % str(created))
                updated = dishData['updated']
                created_time = calendar.timegm(created.utctimetuple()) * 1000 + created.microsecond / 1000
                updated_time = calendar.timegm(updated.utctimetuple()) * 1000 + updated.microsecond / 1000

				# collect the list of current spacecraft targets from the signal
				# reports
                targets = {}
                isTesting = False
                for signalData in (dishData.get('down_signal', []) + dishData.get('up_signal', [])):
                    if signalData['spacecraft_id']:
                        spacecraft = self.get_spacecraft(signalData)
                        if spacecraft:
                            targets[spacecraft.id] = True
                            if 'Testing' in spacecraft.flags:
                                isTesting = True
                if isTesting:
                    if flags != '':
                        flags += ','
                    flags += 'Testing'
                targetList = targets.keys()

                # find the previous version of this record
                if not self.dishHist:
                    self.dishHist = {}
                if is_backdated:
                    histEntry = (DataDish.select(DataDish)
                            .join(DataEvent, on=(DataDish.eventid==DataEvent.id))
                            .where((DataDish.configdishid==dish.id)&(DataEvent.time < is_backdated))
                            .order_by(DataEvent.time.desc())
                            .limit(1).first())
                elif dish.id in self.dishHist:
                    histEntry = self.dishHist[dish.id]
                else:
                    histEntry = (DataDish.select(DataDish)
                            .join(DataEvent, on=(DataDish.eventid==DataEvent.id))
                            .where(DataDish.configdishid==dish.id)
                            .order_by(DataEvent.time.desc())
                            .limit(1).first())
                    if histEntry:
                        self.dishHist[dish.id] = histEntry

                # has there been any change to this record?
                if not self.signalHist:
                    self.signalHist = {}
                if not self.detailHist:
                    self.detailHist = {}
                if (not histEntry or histEntry.createdtime != created_time or
                        histEntry.updatedtime != updated_time or
                        histEntry.flags != flags or
                        histEntry.targetspacecraft1 != (targetList[0] if len(targetList) > 0 else None) or
                        histEntry.targetspacecraft2 != (targetList[1] if len(targetList) > 1 else None) or
                        histEntry.targetspacecraft3 != (targetList[2] if len(targetList) > 2 else None)):
                    histEntry = DataDish.create(
                        configdishid = dish.id,
                        eventid = eventid,
                        createdtime = created_time,
                        updatedtime = updated_time,
                        flags = flags,
                        targetspacecraft1 = targetList[0] if len(targetList) > 0 else None,
                        targetspacecraft2 = targetList[1] if len(targetList) > 1 else None,
                        targetspacecraft3 = targetList[2] if len(targetList) > 2 else None
                    )
                    self.dishHist[dish.id] = histEntry
                    signalHist = {}
                    self.signalHist[dish.id] = signalHist
                    detailHist = {}
                    self.detailHist[dish.id] = detailHist
                elif is_backdated:
                    (signalHist, detailHist) = self.collect_signals(histEntry, is_backdated)
                elif not dish.id in self.signalHist:
                    (signalHist, detailHist) = self.collect_signals(histEntry, None)
                    self.signalHist[dish.id] = signalHist
                    self.detailHist[dish.id] = detailHist
                else:
                    signalHist = self.signalHist[dish.id]
                    detailHist = self.detailHist[dish.id]

                # grab target history, if we have any
                if not self.targetHist:
                    self.targetHist = {}
                if is_backdated:
                    targetHist = {}
                else:
                    if not(dish.id in self.targetHist):
                        self.targetHist[dish.id] = {}
                    targetHist = self.targetHist[dish.id]

                self.punch_targets(eventid, is_backdated, dish, dishData['targets'], targetOut, targetHist)
                self.punch_signals(eventid, dish, histEntry, dishData['down_signal'], dishData['up_signal'],
                    arrayedSignals, signalHist, detailHist, signalOut)

                if (dishData['azimuth_angle'] is not None and
                        dishData['elevation_angle'] is not None and
                        dishData['wind_speed'] is not None):
                    dishOut.append({
                        'configdishid': dish.id,
                        'eventid': eventid,
                        'azimuthangle': dishData['azimuth_angle'],
                        'elevationangle': dishData['elevation_angle'],
                        'windspeed': dishData['wind_speed']
                    })

            if len(dishOut) > 0:
                cmd = DataDishPos.insert_many(dishOut)
                cmd.execute()
            if len(targetOut) > 0:
                cmd = DataTarget.insert_many(targetOut)
                cmd.execute()
            if len(signalOut) > 0:
                cmd = DataSignalDet.insert_many(signalOut)
                cmd.execute()

    def punch_targets(self, eventid, is_backdated, dish, targets, targetOut, targetHist):
        for targetName in targets:
            targetData = targets[targetName]

            # identify the target spaceship
            spacecraft = self.get_spacecraft(targetData)
            if not spacecraft:
                return

            if targetData['down_range'] != -1 or targetData['up_range'] != -1 or targetData['rtlt'] != -1:

                # find the previous version of this record
                if is_backdated:
                    histEntry = (DataTarget.select(DataTarget)
                        .join(DataEvent, on=(DataTarget.eventid==DataEvent.id))
                        .where(
                            (DataTarget.configdishid==dish.id) &
                            (DataTarget.configspacecraftid==spacecraft.id) &
                            (DataEvent.time < is_backdated)
                        )
                        .order_by(DataEvent.time.desc())
                        .limit(1).dicts().first())
                    if histEntry:
                        targetHist[spacecraft.id] = histEntry
                elif spacecraft.id in targetHist:
                    histEntry = targetHist[spacecraft.id]
                else:
                    histEntry = (DataTarget.select(DataTarget)
                        .join(DataEvent, on=(DataTarget.eventid==DataEvent.id))
                        .where((DataTarget.configdishid==dish.id) & (DataTarget.configspacecraftid==spacecraft.id))
                        .order_by(DataEvent.time.desc())
                        .limit(1).dicts().first())
                    if histEntry:
                        targetHist[spacecraft.id] = histEntry

                # if there has been a change, create a new record
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

    def collect_signals(self, dataDish, is_backdated):
        query = (DataSignal.select(DataSignal.eventid)
                .join(DataEvent, on=(DataSignal.eventid==DataEvent.id)))
        if is_backdated:
            query = query.where((DataSignal.datadishid == dataDish.id) & (DataEvent.time < is_backdated))
        else:
            query = query.where(DataSignal.datadishid == dataDish.id)
        eventId = query.order_by(DataEvent.time.desc()).limit(1).scalar()

        results = {}
        details = {}
        if eventId:
            prevEntry = None
            for entry in (DataSignal.select().where(
                        (DataSignal.datadishid == dataDish.id) & (DataSignal.eventid == eventId)
                    ).order_by(
                        DataSignal.updown.asc(),
                        DataSignal.configspacecraftid.asc(),
                        DataSignal.flags.desc(),
                        DataSignal.id.asc()
                    )):
                if (not prevEntry or prevEntry.configspacecraftid != entry.configspacecraftid or
                        prevEntry.updown != entry.updown):
                    seq = 1
                elif prevEntry.configspacecraftid == entry.configspacecraftid and prevEntry.flags < entry.flags:
                    pass # slave connection
                else:
                    seq = seq + 1
                key = (unicode(entry.configspacecraftid) + ('u' if entry.updown == 'up' else 'd') +
                    ':' + unicode(seq) + ('s' if 'slave' in entry.flags.lower() else ''))
                results[key] = entry

                query = (DataSignalDet.select(DataSignalDet.datarate, DataSignalDet.frequency, DataSignalDet.power)
                    .join(DataEvent, on=(DataSignalDet.eventid==DataEvent.id)))
                if is_backdated:
                    query = query.where((DataSignalDet.datasignalid == entry.id) & (DataEvent.time < is_backdated))
                else:
                    query = query.where(DataSignalDet.datasignalid == entry.id)
                details[entry.id] = query.order_by(DataEvent.time.desc()).limit(1).dicts().first()

                prevEntry = entry
        return (results, details)

    def collect_parsed_signals(self, signals, isUp, arrayedSignals, ourSignals):
        # collect and identify the signals so we can match them up to previous signal reports
        signalList = []
        for signalData in signals:
            # identify the target spacecraft
            if not signalData['debug']:
                continue
            spacecraft = self.get_spacecraft(signalData)
            if not spacecraft:
                continue

            state = self.get_state(signalData['debug'], isUp, signalData['type'])

            #collect signal flags
            flags = set()
            flagsort = 0
            if arrayedSignals and spacecraft.id in arrayedSignals:
                if arrayedSignals[spacecraft.id] == signalData:
                    flags.add('master')
                    flagsort = 1
                else:
                    flags.add('slave')
                    flagsort = 2

            # side effect - punch the spacecraft with its last known protocol
            if spacecraft and state.encoding and state.encoding != 'UNC' and spacecraft.encoding != state.encoding:
                spacecraft.encoding = state.encoding
                spacecraft.save()

            signalList.append({
                'isUp': isUp,
                'spacecraft': spacecraft,
                'spacecraft_id': spacecraft.id,
                'state': state,
                'flags': flags,
                'data': signalData,
                'flagsort': flagsort,
                'frequency': signalData['frequency']
            })

        seq = 1
        prevEntry = None
        for entry in sorted(signalList, key=itemgetter('spacecraft_id', 'flagsort', 'frequency')):
            if (not prevEntry or prevEntry['spacecraft_id'] != entry['spacecraft_id']):
                seq = 1
            elif (prevEntry['spacecraft_id'] == entry['spacecraft_id'] and
                    prevEntry['flagsort'] < entry['flagsort']):
                pass # slave connection
            else:
                seq = seq + 1

            # create a unique id for this signal
            key = (unicode(entry['spacecraft_id']) + ('u' if isUp else 'd') +
                ':' + unicode(seq) + ('s' if 'slave' in entry['flags'] else ''))
            ourSignals[key] = entry
            prevEntry = entry

    def punch_signals(self, eventid, dish, dataDish, signalDown, signalUp, arrayedSignals, signalHist, detailHist, signalOut):

        # collect the signals
        ourSignals = {}
        self.collect_parsed_signals(signalDown, False, arrayedSignals, ourSignals)
        self.collect_parsed_signals(signalUp, True, None, ourSignals)

        # has anything changed in these signals?
        isChanged = False
        if len(ourSignals) != len(signalHist):
            self.log.info('CHANGED: %d != %d' % (len(ourSignals), len(signalHist)))
            isChanged = True

        if not isChanged:
            for key in ourSignals:
                entry = ourSignals[key]
                state = entry['state']

                # if we don't have a corresponding entry in the history, or the entry is different,
                # then we have a change
                histEntry = signalHist.get(key, None)
                if (not histEntry) or (histEntry.stateid != state.id):
                    if not histEntry:
                        self.log.info('CHANGED: no entry %s' % key)
                        pprint(signalHist)
                    else:
                        self.log.info('CHANGED(%s on %d): %d -> %s[%d]' % (key, histEntry.configspacecraftid, histEntry.stateid, state.name, state.id))
                    isChanged = True
                    break

        # now process the signals, including any changes if necessary
        if isChanged:
            signalHist.clear()
            detailHist.clear()
        for key in ourSignals:
            entry = ourSignals[key]
            state = entry['state']
            if isChanged:
                # our state has changed, create a new signal record
                spacecraft = entry['spacecraft']
                self.log.info('new signal(%s on %d) has state=%s[%d], flags=%s' % (key, spacecraft.id, state.name, state.id, ','.join(entry['flags'])))
                baseSignal = DataSignal.create(
                    eventid=eventid,
                    datadishid=dataDish.id,
                    configdishid=dish.id,
                    updown='up' if entry['isUp'] else 'down',
                    stateid=state.id,
                    configspacecraftid=spacecraft.id,
                    flags=','.join(entry['flags'])
                )
                signalHist[key] = baseSignal
            else:
                baseSignal = signalHist[key]

            # create a new signal report
            if not(state.valuetype in ('none','idle','idle+')):
                signalData = entry['data']
                lastSignalData = detailHist.get(baseSignal.id, None)
                if (not lastSignalData or lastSignalData['datarate'] != signalData['data_rate'] or
                        lastSignalData['frequency'] != signalData['frequency'] or
                        lastSignalData['power'] != signalData['power']):
                    # self.log.info('signal %s: rate=%s, freq=%s, power=%s' % (key, signalData.get('data_rate',''), signalData.get('frequency',''), signalData.get('power','')))
                    newRecord = {
                        'eventid': eventid,
                        'datasignalid': baseSignal.id,
                        'datarate': signalData['data_rate'],
                        'frequency': signalData['frequency'],
                        'power': signalData['power']
                    }
                    detailHist[baseSignal.id] = newRecord
                    signalOut.append(newRecord)

    def get_state(self, debug, isUp, signalType):
        state = self.existingStates.get(debug, None)
        if state:
            return state

        parsed = parse_debug(debug, isUp)
        state = ConfigState.create(
            name = debug,
            updown = 'UP' if isUp else 'down',
            signaltype = signalType,
            decoder1 = parsed.get('decoder1', None),
            decoder2 = parsed.get('decoder2', None),
            encoding = parsed.get('encoding', None),
            task = parsed.get('task', None),
            flags = ','.join(parsed.get('flags', set())),
            valuetype = parsed.get('valueType', None)
        )
        self.existingStates[state.name] = state
        return state

    def get_spacecraft(self, targetData):
        targetName = targetData['spacecraft'] or ''
        targetId = targetData['spacecraft_id']

        # first look it up by name
        spacecraft = self.spacecraftById.get(targetId, None)
        if spacecraft:
            return spacecraft if spacecraft.name.lower() == targetName.lower() else None

        # couldn't find it by id, find it by name
        spacecraft = self.spacecraftByName.get(targetName.lower(), None)
        if spacecraft:
            # If we don't know the official spacecraft_id, push it to the ConfigSpacraft table
            if self.spacecraftById.get(targetId, None) != spacecraft:
                spacecraft.lastid = targetId
                spacecraft.save()
                self.spacecraftById[targetId] = spacecraft
            return spacecraft

        # couldn't find it anywhere, let's create it as a testing "spacecraft"
        spacecraft = ConfigSpacecraft.create(lastid=targetId, name=targetName, flags='Testing')
        self.spacecraftByName[targetName.lower()] = spacecraft
        self.spacecraftById[targetId] = spacecraft
        return spacecraft

if __name__ == '__main__':
    import dsn_db
    logging.basicConfig(level=logging.INFO)
    dsn = dsn_db.DSN_DB()
    sync = DBSync()
    dsn.data_callback = sync.punch_data
    dsn.config_callback = sync.sync_config
    dsn.run()
