#!/usr/bin/env python3.7

import os
import queue
import time
import logging
import threading
import signal

from functools import partial
from logging.handlers import RotatingFileHandler

import xml.etree.ElementTree as ET
import concurrent.futures

from pyaltitude.config import Config
from pyaltitude.worker import Worker
from pyaltitude.enums import PyaltEnum
#from pyaltitude.custom_commands import attach

from inotify_simple import INotify, flags
import ujson

logger = logging.getLogger('pyaltitude')


class TailThread(threading.Thread):
    logger = logging.getLogger('pyaltitude.TailThread')

    def __init__(self, config, queue):
        self.config = config
        self.queue = queue
        self._buffer = ''

        super(TailThread, self).__init__(daemon=True)


    def run(self, rollover=False):
        if rollover:
            self.logger.info("Tailing log file after rollover at %s" % self.config.log_path)
        else:
            self.logger.info('Begin tailing log file at %s' % self.config.log_path)

        with open(self.config.log_path, 'rt') as fh:
            try:
                inotify = INotify()
            except IsADirectoryError as e:
                #inotify_simple known issue
                #https://github.com/chrisjbillington/inotify_simple/issues/17
                self.logger.critical('inotify_simple version error on this kernel')
                self.queue.put(PyaltEnum.INOTIFY_ERR)
                return


            mask = flags.MODIFY | flags.MOVE_SELF
            wd = inotify.add_watch(self.config.log_path, mask)

            while True:
                do_break = False
                for event in inotify.read():
                    for flag in flags.from_mask(event.mask):
                        if flag is flags.MOVE_SELF:
                            # rollover is happening
                            self.logfile_modified(fh)
                            do_break = True
                        elif flag is flags.MODIFY:
                            self.logfile_modified(fh)

                if do_break:
                    break

        inotify.close()
        self.run(rollover=True)


    def logfile_modified(self, fh):
        self._buffer += fh.read()
        events = self._buffer.split('\n')

        if not events[-1].endswith('}'):
            #its not a full event, put it back in the buffer
            self._buffer = events[-1]
            del events[-1]

        for event in events:
            self.route_event(self.parse_event(event))


    def parse_event(self, event):
        try:
            event = ujson.loads(event)
        except ValueError:
            self.logger.error("Could not parse log line: %s" % event)
            raise
        return event


    def route_event(self, event):
        if event['port'] != -1:
            #send to the execute on the specific server
            server = self.config.get_server(event['port'])
            server.queue.put(event)
            #self.logger.debug('Events in %s queue: %s' % (server.serverName, server.queue.qsize()))
        else:
            #execute on the default thread
            self.queue.put(event)


class Main(object):

    def setup_logging(self, logfile, debug):
        formatter = logging.Formatter('%(asctime)s - %(name)35s - %(levelname)10s - %(message)s')

        if debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        logger.addHandler(sh)

        logger.info("Starting up.")

        if logfile:
            fh = RotatingFileHandler(filename=logfile, maxBytes=5*1024*1024, backupCount=10)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
            logger.info("Logging to file at %s" % logfile)


    def shutdown(self, signum, frame):
        logger.warning("Shutting down after receiving %s" % ("SIGINT" if signum == 2 else "SIGTERM"))
        #check all the servers and send them a message to logout
        # this is ugly!
        servers_with_players = self.config.server_manager.servers_with_players()
        if servers_with_players:
            t = 30
            msg = "Shutting down server in %s seconds, please end your session. Sorry!"
            logger.warning("Giving logged in players %s seconds to log out before they will be dropped" % t)
            do_break = True
            while t > 0:
                for server in servers_with_players:
                    if not t%10:
                        logger.warning('Shutdown in %s' % t)
                        server.serverMessage(msg % t)
                    elif t < 6:
                        server.serverMessage(msg % t)
                t -= 1
                time.sleep(1)

        # drop any players on the servers, and shutdown the
        # altitude server itself
        self.config.server_manager.shutdown(alti_server=True)
        self.queue.put(PyaltEnum.SHUTDOWN)


    def run(self, conf='./pyalt.yaml', logfile=None, debug=False):
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)

        self.setup_logging(logfile, debug)

        self.config = Config(conf)
        self.queue = queue.Queue()

        self.config.start_servers()


        tail_thread = TailThread(self.config, self.queue)
        tail_thread.start()

        """
        Not sure if this deserves to be here, but its such an insidiuos error,
        im going to leave it for now.
        """
        if not self.queue.empty() and self.queue.get(timeout=0.5) == PyaltEnum.INOTIFY_ERR:
            print()
            print("Your system appears to be an older kernel that requires running a")
            print("specific version of inotify_simple.  Please install it by running:")
            print()
            print("pip install inotify_simple==1.2.1")
            print()
            print("More info here: https://github.com/chrisjbillington/inotify_simple/issues/17")
            return


        logger.info('Waiting for events on main thread')
        while True:
            data = self.queue.get()
            if data == PyaltEnum.SHUTDOWN:
                break

            worker = Worker(data, self.config, modules=list())
            worker.execute()

        logger.info('Done.')


if __name__ == "__main__":
    from datetime import datetime
    
    Main().run(conf='./pyalt.yaml', logfile='./PYALTITUDE_%s.log' % datetime.now(), debug=False)


