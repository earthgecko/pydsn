# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
import time
import logging
from requests.exceptions import ConnectionError
from lxml.etree import LxmlError
from dsnparser import DSNParserDB
import traceback
import resource

logfile = '/var/log/pydsn/dsn_dbsync.log'
app = 'dsn_db'
# logging.basicConfig(filename=logfile, level=logging.INFO)
logging.basicConfig(
    filename=logfile,
    filemode='a',
    level=logging.INFO,
    format="%(asctime)s :: %(process)s :: %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S')

LOCAL_DEBUG = False


class DSN_DB(object):
    def __init__(self):
        self.stdout_path = logfile
        self.stderr_path = logfile
        self.log = logging.getLogger(__name__)
        self.parser = DSNParserDB()
        self.next_config_update = 0
        self.next_data_update = 0
        self.status_update_interval = 10  # Seconds
        self.config_update_interval = 600  # Seconds
        self.config_callback = None
        self.data_callback = None    # Called for every new data update

    def update(self):
        try:
            now = time.time()
            if self.next_config_update <= now:
                self.next_config_update = now + self.config_update_interval
                self.sites, self.spacecraft = self.parser.fetch_config()
                if self.config_callback:
                    self.config_callback(self.sites, self.spacecraft)
                    self.log.info('%s :: config processing complete' % app)

            now = time.time()
            if self.next_data_update <= now:
                self.next_data_update = (int)(now / self.status_update_interval + 1) * self.status_update_interval
                new_data = self.parser.fetch_data()
                if self.data_callback:
                    if not self.data_callback(new_data):
                        self.log.info('%s :: status processing rejected' % app)
                    else:
                        self.log.info('%s :: status processing complete' % app)

        except ConnectionError, e:
            self.log.warn('%s :: unable to fetch data from DSN: %s' % (app, str(e)))
            return
        except LxmlError, e:
            self.log.warn('%s :: unable to parse data: %s' % (app, str(e)))
            return

    def run(self):
        while True:
            try:
                if LOCAL_DEBUG:
                    self.log.info('%s :: debug :: Memory usage start self.update: %s (kb)' % (app, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
                self.update()
            except:
                self.log.info(traceback.format_exc())
                self.log.info('error :: %s :: self.update() error' % app)
                pass

            if LOCAL_DEBUG:
                self.log.info('%s :: debug :: Memory usage end self.update: %s (kb)' % (app, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))

            # time.sleep(1)
            time.sleep(self.status_update_interval)
