# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
from time import sleep
import time
import logging
from datetime import datetime
from datetime import timedelta
from requests.exceptions import ConnectionError
from lxml.etree import LxmlError
from parser import DSNParser
import urllib
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
# from multiprocessing import Process, Manager
import resource
import traceback

logfile = '/var/log/pydsn/dsn.log'
app = 'dsn'
# logging.basicConfig(filename=logfile, level=logging.INFO)
logging.basicConfig(
    filename=logfile,
    filemode='a',
    level=logging.INFO,
    format="%(asctime)s :: %(process)s :: %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S')

LOCAL_DEBUG = False

heapy_enabled = False
if heapy_enabled:
    from guppy import hpy


class DSN(object):
    def __init__(self):
        self.stdout_path = logfile
        self.stderr_path = logfile
        self.log = logging.getLogger(__name__)
        self.parser = DSNParser()
        self.last_config_update = None
        # @added 20160902 - Merging russss and odysseus654
        self.next_config_update = 0
        self.next_data_update = 0

        # self.status_update_interval = 5  # Seconds
        self.status_update_interval = 10  # Seconds
        self.config_update_interval = 600  # Seconds
        self.data = None
        self.update_callback = None  # Called per-antenna if the status has changed
        # @added 20160902 - Merging russss and odysseus654
        self.config_callback = None
        self.data_callback = None    # Called for every new data update
        # self.manager = Manager()

    def update(self):
        try:
            # Attempt at multiprocessing does not work
            # from parser import DSNParser
            # parser = DSNParser()
            if self.last_config_update is None or \
               self.last_config_update < datetime.now() - timedelta(minutes=self.config_update_interval):
                self.sites, self.spacecraft = self.parser.fetch_config()
                # self.sites, self.spacecraft = parser.fetch_config()
            new_data = self.parser.fetch_data()
            # new_data = parser.fetch_data()
            self.log.info('dsn :: new data fetched from DSN')
        except ConnectionError, e:
            self.log.warn('dsn :: unable to fetch data from DSN: %s' % e)
            return
        except LxmlError, e:
            self.log.warn('dsn :: unable to parse data: %s', e)
            return

        if self.data is not None:
            self.compare_data(self.data, new_data)
            if self.data_callback:
                self.data_callback(self.data, new_data)

        self.data = new_data

    def compare_data(self, old, new):
        if not self.update_callback:
            return

        for antenna, new_status in new.iteritems():
            if antenna not in old:
                # Antenna has gone away (oh no)
                continue
            old_status = old[antenna]
            # The "updated" flag doesn't get flipped except for especially significant status
            # changes, but we care about them all
            updated = new_status['updated'] > old_status['updated']
            for signal in ('down_signal', 'up_signal'):
                if (len(new_status[signal]) > 0 and len(old_status[signal]) == 0) or \
                   (len(new_status[signal]) > 0 and
                        new_status[signal][0]['debug'] != old_status[signal][0]['debug']):
                    updated = True
                    self.log.info('data updates found')
            if updated:
                self.update_callback(antenna, old_status, new_status)

    def run(self):
        while True:
            # self.log.info('%s :: debug :: Memory usage start self.update: %s (kb)' % (app, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
            if heapy_enabled:
                hp = hpy()
                before = hp.heap()
                self.log.info('%s :: debug :: heapy dump in before before self.update')
                self.log.info(before)
            try:
                self.update()
            except:
                return

            if LOCAL_DEBUG:
                self.log.info('%s :: debug :: Memory usage end self.update: %s (kb)' % (app, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))

            if heapy_enabled:
                after = hp.heap()
                self.log.info('%s :: debug :: heapy dump after self.update' % app)
                self.log.info(after)
                self.log.info('%s :: debug :: heapy dump leftover after self.update' % app)
                leftover = after - before
                self.log.info(leftover)

            # Attempt at multiprocessing does not work
            # self.log.info('dsn :: spawning process to fetch data from DSN')
            # spawned_pids = []
            # p = Process(target=self.update())
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
            #    raise TimeoutError

            # for pid in spawned_pids:
            #     self.log.info('dsn :: spawned pid %s fetched data' % str(pid))

            sleep(self.status_update_interval)
            # return
