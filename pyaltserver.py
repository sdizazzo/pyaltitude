#!/usr/bin/env python3.7

import os
import queue
import time
import logging
import threading

from logging.handlers import RotatingFileHandler

import xml.etree.ElementTree as ET
import concurrent.futures

from pyaltitude.config import Config
from pyaltitude.worker import Worker
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
                self.queue.put(99)
                return


            mask = flags.MODIFY | flags.MOVE_SELF
            wd = inotify.add_watch(self.config.log_path, mask)

            while True:
#                #check for queued events from the servers as well!
#                event_from_server = self.queue.get_nowait()
#                if event_from_server:
#                    self.logger.info('Got event back from server: %s' % server)# not sure what this is going to look like yet
#                    self.process_server_event(event_from_server)

                do_break = False
                for event in inotify.read():
                    for flag in flags.from_mask(event.mask):
                        if flag is flags.MOVE_SELF:
                            # rollover is happening
                            self.logfile_modified(fh)
                            do_break = True
                        elif flag is flags.MODIFY:
                            self.logfile_modified(fh)

                if do_break: break

        self.run(rollover=True)


#    def process_server_event(self, server_event):
#        #eventually pass this to a class
#        #first off, parse the json and getPlayers
#
#        #{'vaporId': '0a29dfcf-26ec-477c-9a48-d7fe035f284a', 
#        #'level': 60, 'ip': '172.112.31.38:36346', 
#        #'type': 'clientAdd','port': 27284, 'nickname': 
#        #'Bukowski', 'time': 40130, 'player': 0}

        


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
        #process all client events on the main thread
        #if event['port'] != -1 and event['type'] not in ('clientAdd', 'clientRemove', 'serverMessage'): #serverWhisper, etc???
        if event['port'] != -1:
            #send to the execute on the thread pool on the specific server
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


    def run(self, conf='./pyalt.yaml', logfile=None, debug=False):
        self.setup_logging(logfile, debug)

        self.config = Config(conf)
        self.queue = queue.Queue()

        self.config.start_server_thread_pools()


        tail_thread = TailThread(self.config, self.queue)
        tail_thread.start()

        if not self.queue.empty() and self.queue.get(timeout=0.5) == 99:
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
            try:
                line = self.queue.get()
                worker = Worker(line, self.config, modules=list())
                worker.execute()
                time.sleep(.1)
            except KeyboardInterrupt:
                logger.info('Done.')
                break
                

if __name__ == "__main__":
    from datetime import datetime
    
    Main().run(conf='./pyalt.yaml', logfile='./PYALTITUDE_%s.log' % datetime.now(), debug=False)

