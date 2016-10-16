# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
from collections import namedtuple, defaultdict, deque
from datetime import datetime, timedelta
import ConfigParser
import logging
import pickle
import tweepy
from tweepy.error import TweepError
from dsn import DSN
# import mock
# import unittest
from time import time, sleep
import resource
# from multiprocessing import Process, Manager
from sys import path
import traceback
from sys import version_info
import os
import errno
import stat

logfile = '/var/log/pydsn/dsn.log'
app = 'tweet_updates'
# logging.basicConfig(filename=logfile, level=logging.INFO)
logging.basicConfig(
    filename=logfile,
    filemode='a',
    level=logging.INFO,
    format="%(asctime)s :: %(process)s :: %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S')

config_file = '%s/dsn.conf' % (path[0])

TESTING = True
heapy_enabled = False
if heapy_enabled:
    from guppy import hpy

python_version = int(version_info[0])

spacecraft_twitter_names = {
    'MSL': 'MarsCuriosity',
    'NHPC': 'NewHorizons2015',
    'ROSE': 'ESA_Rosetta',
    'CAS': 'CassiniSaturn',
    'MOM': 'MarsOrbiter',
    'KEPL': 'NASAKepler',
    'ORX': 'OSIRISREx',
    'TGO': 'ESA_TGO'
}

dscc_locations = {
    'mdscc': (40.429167, -4.249167),
    'cdscc': (-35.401389, 148.981667),
    'gdscc': (35.426667, -116.89)
}

# @added 20160927 - Feature #1624: tweets table
# Added dscc_locations_country
dscc_locations_country = {
    'mdscc': 'ES',
    'cdscc': 'AU',
    'gdscc': 'US'
}


def to_GHz(freq):
    if freq is None:
        return None
    return str(round(float(freq) / 10 ** 9, 4))


def format_datarate(rate):
    if rate < 1000:
        return "%sb/s" % (int(rate))
    elif rate < 500000:
        return "%skb/s" % (round(rate / 1000, 1))
    else:
        return "%sMb/s" % (round(rate / 1000000, 1))

# This state represents the per-spacecraft data which needs to change
# in order to (possibly) generate a tweet
State = namedtuple("State", ['antenna',   # Antenna identifier
                             'status',    # Status (none, carrier, data)
                             'data',
                             'timestamp'
                             ])


def state_changed(a, b):
    # Avoid announcing antenna changes at the moment, as
    # it causes flapping if two antennas are receiving one craft simultaneously.
    return not (a.status == b.status)


def combine_state(signals):
    """ Given a number of signals from a spacecraft, find the most notable. """
    if len(signals) == 1:
        data = signals[0]
        status = data['type']
    else:
        status = 'none'
        data = signals[0]  # Pick one signal in case we don't find a more interesting one
        for signal in signals:
            if signal['type'] == 'carrier' and status == 'none':
                status = 'carrier'
                data = signal
            elif signal['type'] == 'data' and status in ('carrier', 'none'):
                status = 'data'
                data = signal
    return State(data['antenna'], status, data, datetime.now())


def mkdir_p(path):
    """
    Create nested directories.

    :param path: directory path to create
    :type path: str
    :return: returns True

    """
    try:
        if python_version == 2:
            mode_arg = int('0755')
        if python_version == 3:
            mode_arg = mode=0o755
        os.makedirs(path, mode_arg)
        return True
    # Python >2.5
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def file_age_in_seconds(pathname):
    return int(time() - os.stat(pathname)[stat.ST_MTIME])


class TweetDSN(object):
    def __init__(self):
        self.stdout_path = logfile
        self.stderr_path = logfile
        self.log = logging.getLogger(__name__)
        self.config = ConfigParser.ConfigParser()
        self.config.read(config_file)
        self.twitter_enabled = self.config.getboolean('twitter', 'twitter_enabled')
        self.hipchat_enabled = self.config.getboolean('hipchat', 'hipchat_enabled')

        self.log.info('%s :: twitter_enabled: %s' % (app, self.twitter_enabled))
        self.log.info('%s :: twitter_enabled: type %s' % (app, str(type(self.twitter_enabled))))
        self.log.info('%s :: hipchat_enabled: %s' % (app, self.hipchat_enabled))

        if self.twitter_enabled:
            # self.config.read('dsntweet.conf')
            auth = tweepy.OAuthHandler(self.config.get('twitter', 'api_key'),
                                       self.config.get('twitter', 'api_secret'))
            auth.set_access_token(self.config.get('twitter', 'access_key'),
                                  self.config.get('twitter', 'access_secret'))
            self.twitter = tweepy.API(auth)

        self.pending_updates = {}
        self.state = {}
        self.last_updates = {}
        self.spacecraft_blacklist = set(['TEST', 'GRAY', 'GBRA', 'DSN', 'VLBI', 'RSTS'])
        # self.manager = Manager()

    def data_callback(self, _old, new):
        signals = defaultdict(list)
        # self.log.info('%s' % str(new))
        for antenna, status in new.iteritems():
            # Spacecraft can have more than one downlink signal, but antennas can also be
            # receiving from more than one spacecraft
            # self.log.info('antenna - %s' % str(antenna))
            # self.log.info('status - %s' % str(status))

            for signal in status['down_signal']:
                signal['antenna'] = antenna
                signals[signal['spacecraft']].append(signal)

        new_state = {}
        for spacecraft, sc_signals in signals.iteritems():
            new_state[spacecraft] = combine_state(sc_signals)

        self.update_state(new_state)
        self.process_updates()

    def update_state(self, new_state):
        for spacecraft, state in new_state.iteritems():
            if spacecraft in self.spacecraft_blacklist:
                continue
            if spacecraft not in self.state:
                # New spacecraft, save its state for future reference:
                self.log.info("New spacecraft seen: %s" % spacecraft)
                self.state[spacecraft] = state
            elif state_changed(self.state[spacecraft], state):
                self.queue_update(spacecraft, state)

    def queue_update(self, spacecraft, state):
        # Do we already have an update queued for this spacecraft?
        if spacecraft in self.pending_updates:
            update = self.pending_updates[spacecraft]
            # Has the state changed since the last update was queued?
            if not state_changed(update['state'], state):
                self.log.debug("Queueing new update for %s: %s", spacecraft, state)
                update['state'] = state
            else:
                # Update has changed, bump the timestamp
                self.log.debug("Postponing update for %s: %s", spacecraft, state)
                update = {'state': state, 'timestamp': datetime.now()}
        else:
            self.pending_updates[spacecraft] = {'state': state, 'timestamp': datetime.now()}

    def process_updates(self):
        new_updates = {}
        tweets = deferred = 0
        for spacecraft, update in self.pending_updates.iteritems():
            if update['timestamp'] < datetime.now() - timedelta(seconds=63):
                tweets += 1
                self.tweet(spacecraft, update['state'])
                self.state[spacecraft] = update['state']
            else:
                deferred += 1
                new_updates[spacecraft] = update
        self.pending_updates = new_updates
        if tweets > 0 or deferred > 0:
            self.log.info('%s :: %s state updates processed, %s updates deferred' % (app, tweets, deferred))

    def tweet(self, spacecraft, state):
        if not self.should_tweet(spacecraft, state):
            self.log.info('%s :: Not tweeting about %s being in state %s' % (app, spacecraft, state))
            return

        if spacecraft in spacecraft_twitter_names:
            sc_name = '@' + spacecraft_twitter_names[spacecraft]
        else:
            sc_name = self.dsn.spacecraft.get(spacecraft.lower(), spacecraft)

        antenna = self.antenna_info(state.antenna)
        if antenna is None or antenna['site'] not in dscc_locations:
            self.log.warn('%s :: Antenna site %s not found in dscc_locations' % (app, antenna))
            return
        lat, lon = dscc_locations[antenna['site']]
        # @added 20160927 - Feature #1624: tweets table
        # Added dscc_locations_country
        country = dscc_locations_country[antenna['site']]
        old_state = self.state[spacecraft]
        message = None
        if state.status == 'carrier' and old_state.status == 'none':
            # @modified 20160927 - Feature #1624: tweets table
            # Added dscc_locations_country
            # message = "%s carrier lock on %s\nFrequency: %sGHz\n" % \
            #           (antenna['friendly_name'], sc_name,
            #            to_GHz(state.data['frequency']))
            message = "%s %s carrier lock on %s\nFrequency: %sGHz\n" % \
                      (country, antenna['friendly_name'], sc_name,
                       to_GHz(state.data['frequency']))
            # Ignore obviously wrong Rx power numbers - sometimes we see a lock before
            # Rx power settles down.
            if state.data['power'] > -200:
                message += "Signal strength: %sdBm\n" % (int(state.data['power']))
            message += state.data['debug']
        if state.status == 'data' and old_state.status in ('none', 'carrier'):
            # @modified 20160927 - Feature #1624: tweets table
            # Added dscc_locations_country
            # message = "%s receiving data from %s at %s.\n%s" % \
            #           (antenna['friendly_name'], sc_name, format_datarate(state.data['data_rate']),
            #            state.data['debug'])
            message = "%s %s receiving data from %s at %s.\n%s" % \
                      (country, antenna['friendly_name'], sc_name,
                       format_datarate(state.data['data_rate']),
                       state.data['debug'])
        if message is not None:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if spacecraft not in self.last_updates:
                self.last_updates[spacecraft] = deque(maxlen=25)
            self.last_updates[spacecraft].append((datetime.now(), state))
            if self.twitter_enabled:
                try:
                    self.twitter.update_status(status=message, lat=lat, long=lon)
                except TweepError:
                    self.log.exception('%s :: Tweet error' % app)
                # print(message)
            else:
                print('%s' % now)
                print(message)
                self.log.info('%s :: tweet - %s' % (app, message))

            # @added 20160909 - Added dsn enable_hipchat - sends tweets to a
            # hipchat room
            if self.hipchat_enabled:
                import hipchat
                sender = self.config.get('hipchat', 'hipchat_bot')
                hipchat_auth_token = self.config.get('hipchat', 'hipchat_auth_token')
                room = self.config.get('hipchat', 'hipchat_room')
                try:
                    hipster = hipchat.HipChat(token=hipchat_auth_token)
                    hipchat_message = '%s UTC - %s' % (str(now), message)
                    hipchat_color = 'purple'
                    hipster.method(
                        'rooms/message', method='POST',
                        parameters={'room_id': room, 'from': sender, 'color': hipchat_color, 'message': hipchat_message})
                    self.log.info('%s :: hipchat - %s - %s' % (app, sender, message))
                except:
                    self.log.exception('error :: %s :: failed to send to hipchat - %s - %s' % (app, sender, message))

    def should_tweet(self, spacecraft, state):
        """ Last check to decide if we should tweet this update. Don't tweet about the same
            (spacecraft, antenna, status) more than once every n hours."""
        if spacecraft not in self.last_updates:
            return True
        for update in self.last_updates[spacecraft]:
            timestamp, previous_state = update
            if (previous_state.status == state.status and
                    previous_state.antenna == state.antenna and
                    timestamp > datetime.now() - timedelta(hours=6)):
                return False
        return True

    def antenna_info(self, antenna):
        for site, site_info in self.dsn.sites.iteritems():
            for ant, antenna_info in site_info['dishes'].iteritems():
                if antenna == ant:
                    return {"site_friendly_name": site_info['friendly_name'],
                            "site": site,
                            "friendly_name": antenna_info['friendly_name']}

    def run(self):
        # logging.basicConfig(level=logging.INFO)
        logging.basicConfig(
            filename=logfile,
            level=logging.INFO,
            format="%(asctime)s :: %(process)s :: %(message)s",
            datefmt='%Y-%m-%d %H:%M:%S')

        self.dsn = DSN()
        self.dsn.data_callback = self.data_callback

        self.log.info('%s :: running' % app)

        try:
            mkdir_p('/tmp/pydsn')
        except:
            self.log.info(str(traceback.format_exc()))
            self.log.info('error :: %s :: could not create /tmp/pydsn' % app)

        try:
            # @modified 20160909 - Move state file to /tmp/pydsn
            # with open("./state.pickle", "r") as f:
            # An supervisor does not stop the process in a way that gets Python
            # to the finally: stage where the state is pickled
            use_pickle_data = True
            if os.path.isfile('/tmp/pydsn/state.pickle'):
                file_age = file_age_in_seconds('/tmp/pydsn/state.pickle')
                if file_age > 60:
                    use_pickle_data = False
                    self.log.info('%s :: not using state pickle data - %s seconds old. resetting' % (app, str(file_age)))
                    try:
                        os.remove('/tmp/pydsn/state.pickle')
                        self.log.info('%s :: removed - %s' % (app, '/tmp/pydsn/state.pickle'))
                    except:
                        self.log.exception('%s :: failed to remove - %s' % (app, '/tmp/pydsn/state.pickle'))
                else:
                    self.log.info('%s :: using state pickle data - %s seconds old' % (app, str(file_age)))
            else:
                use_pickle_data = False
                self.log.info('%s :: not using state pickle data - %s - not found' % (app, '/tmp/pydsn/state.pickle'))

            if use_pickle_data:
                try:
                    with open('/tmp/pydsn/state.pickle', 'r') as f:
                        self.state, self.last_updates = pickle.load(f)
                    self.log.info('%s :: load state from pickle' % app)
                except IOError:
                    self.log.exception("Failure loading state file, resetting")
        except:
            self.log.exception('error :: %s :: failure loading state file' % app)

        try:
            self.log.info('%s :: debug :: self.state pickle - %s' % (app, str(self.state)))
        except:
            self.log.info(str(traceback.format_exc()))
            self.log.info('error :: %s :: could not determine self.state pickle' % app)

        # self.log.info('%s :: debug :: Memory usage start dsn.run: %s (kb)' % (app, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
        if heapy_enabled:
            hp = hpy()
            before = hp.heap()
            self.log.info('%s :: debug :: heapy dump in before before dsn.run' % app)
            self.log.info(before)

        try:
            self.dsn.run()
        finally:
            self.log.info('%s :: debug :: Memory usage end dsn.run: %s (kb)' % (app, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
            self.log.info('%s :: Saving state...' % (app))
            try:
                # @modified 20160909 - Move state file to /tmp/pydsn
                # with open("./state.pickle", "w") as f:
                with open('/tmp/pydsn/state.pickle', 'w') as f:
                    pickle.dump((self.state, self.last_updates), f, pickle.HIGHEST_PROTOCOL)
            except IOError:
                self.log.exception('error :: %s :: failed to write state file' % app)
            if heapy_enabled:
                after = hp.heap()
                self.log.info('%s :: debug :: heapy dump in analyzer_debug after dsn.run' % app)
                self.log.info(after)
                self.log.info('%s :: debug :: heapy dump leftover after dsn.run' % app)
                leftover = after - before
                self.log.info(leftover)
            self.log.info("%s :: Shut down." % app)

TweetDSN().run()

# while True:
#    TweetDSN().run()
#    sleep(10)

    # Attempt at multiprocessing does not work
    # self.log.info('dsn :: spawning process to fetch data from DSN')
    # spawned_pids = []
    # p = Process(target=TweetDSN().run())
    # p.start()
    # spawned_pids.append(p.pid)
    # for pid in spawned_pids:
    #     self.log.info('dsn :: spawned pid %s to fetch data from DSN' % str(pid))

    # Force a max. `timeout` or wait for the process to finish
    # p.join(9)

    # If thread is still active, it didn't finish: raise TimeoutError
    # if p.is_alive():
    #     p.terminate()
    #     p.join()
    #     for pid in spawned_pids:
    #         self.log.info('error :: dsn :: spawned pid %s failed to fetch data, timeout reached' % str(pid))
        # raise TimeoutError

    # for pid in spawned_pids:
    #     self.log.info('dsn :: spawned pid %s fetched data' % str(pid))
    # sleep(10)
