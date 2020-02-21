#!/usr/bin/env python3.7

import os
import queue
import time
import logging
import threading

from logging.handlers import RotatingFileHandler
from functools import partial

import xml.etree.ElementTree as ET
import concurrent.futures

import ujson # faster than built-in but we have small data
             # not sure it justifies a requirement

#TODO config module
# paths are currently hardcoded in individual mods
PATH = '/home/sean/altitude/servers/log.txt'
COMMAND_PATH = '/home/sean/altitude/servers/command.txt'
LAUNCHER_CONFIG = '/home/sean/altitude/servers/launcher_config.xml'


from pyaltitude import commands
from pyaltitude.base import Base
from pyaltitude.events import Events
from pyaltitude.map import Map
from pyaltitude.enums import MapState
from pyaltitude.player import Player
from pyaltitude.server import Server
from pyaltitude.modules import *
#from pyaltitude.custom_commands import attach



logger = logging.getLogger('pyaltitude')



class Worker(Events):
    logger = logging.getLogger('pyaltitude.Worker')

    def __init__(self, line, init, servers, thread_lock):
        self.line = line
        self.init = init
        self.servers = servers
        self.thread_lock = thread_lock


    def execute(self):
        #I don't believe its worth the overhead of setting up a logger here
        # just to get the thread number executing
        #self.logger = logging.getLogger('pyaltitude.%s' % threading.current_thread().name)
        def get_module_events(module):
            events = list()
            for func in dir(module):
                if callable(getattr(module, func)) and not func.startswith('__'):
                    events.append(func)
            return events


        #####
        #NOTE HACK!!!!!!!!!!!!!!!!!!!!!!!!

        # NEED LOAD MODULE AND UNLOAD MODULES BASED ON GAME MODE OR MAP OR
        # SERVER
        # 
        # Will do for all (server?) modules
        mods = (king_of_the_hill.KOTH, )
        for module in mods:
            module.servers = self.servers
            for func_name in get_module_events(module()):
                func = getattr(module(), func_name)
                setattr(self, func_name, func)

        try:
            event = ujson.loads(self.line)
        except ValueError:
            self.logger.error("Worker could not parse log line: %s" % self.line)
            raise

        try:
            self.logger.debug("Processing event %s" % event)
            method = getattr(self, event['type'])
        except AttributeError as e:
            #self.logger.warning(repr(NotImplementedError(event['type'])))
            return
        
        method(event, self.init, self.thread_lock)



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


    def run(self, logfile=None, debug=False):
        self.setup_logging(logfile, debug)

        self.servers = self.parse_server_config()
        self.queue = queue.Queue()
        self.thread_lock = threading.Lock()

        ##################
        # NOTE
        #
        # parse config here and pass in
        # also determine which modules to load 
        # and pass in through to workers

        tail_thread=threading.Thread(target=self.tail, daemon=True)
        tail_thread.start()


        with concurrent.futures.ThreadPoolExecutor(min(32, os.cpu_count() + 4), thread_name_prefix='Worker') as pool:
            # one NOTE is that I dont want to have to load modules
            # on every event worry about that later
            logger.info('Initialized thread pool')
            while True:
                try:
                    (line, INIT) = self.queue.get()
                    worker = Worker(line, INIT, self.servers, self.thread_lock)
                    future = pool.submit(worker.execute)
                    future.add_done_callback(self.worker_done_cb)
                    time.sleep(.01)
                except KeyboardInterrupt:
                    logger.info('Done.')
                    break


    def worker_done_cb(self, fut):
        exception = fut.exception()
        if exception:
            try:
                # get the result so we raise the exception
                # and get the traceback
                fut.result()
            except Exception as e:
                logger.exception('Worker raised exception: %s' % repr(e))


    def tail(self, rollover=False):
        if rollover:
            logger.info("Tailing log file after rollover at %s" % PATH)
        else:
            logger.info('Begin tailing log file at %s' % PATH)

        with open(PATH, 'rt') as f:
            inode = os.fstat(f.fileno()).st_ino
            while True:
                line = f.readline()
                if not line:
                    if os.stat(PATH).st_ino != inode:
                        break
                    time.sleep(0.01)
                    continue
                self.queue.put((line, False))

        self.tail(rollover=True)


    def parse_server_config(self):
        servers = dict()

        logger.info('Parsing server config file at: %s' % LAUNCHER_CONFIG)
        with open(LAUNCHER_CONFIG, 'rt') as f:
            contents = f.read()

        root = ET.fromstring(contents)
        for server_config in root.iter("AltitudeServerConfig"):
            server = Server()
            server = server.parse(server_config.attrib)
            servers[server.port] = server

        mapList = root.find('mapList')
        return servers
 

if __name__ == "__main__":
    
    from datetime import datetime
    
    Main().run(logfile='./PYALTITUDE_%s.log' % datetime.now(), debug=False)


