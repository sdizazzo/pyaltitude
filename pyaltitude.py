#!/usr/bin/env python3.7

import os
import asyncio
import aiofiles
import ujson
import xml.etree.ElementTree as ET
import concurrent.futures
import queue
import time
import logging
import traceback
from threading import Lock
from functools import partial

from aiologger import Logger
logging.basicConfig(level=logging.DEBUG)
import threading

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



class Worker(Events):
    logger = Logger.with_default_handlers(name='pyaltitude.Worker')

    def __init__(self, line, init, servers, thread_lock):
        self.line = line
        self.init = init
        self.servers = servers
        self.thread_lock = thread_lock

    def execute(self):
        def get_module_events(module):
            events = list()
            for func in dir(module):
                if callable(getattr(module, func)) and not func.startswith('__'):
                    events.append(func)
            return events


        #####
        #NOTE HACK!!!!!!!!!!!!!!!!!!!!!!!!
        #testing attaching the module dynamically

        # NEED LOAD MODULE AND UNLOAD MODULES BASED ON GAME MODE OR MAP OR
        # SERVER
        # 
        # Will do for all (server?) modules
        mods = (king_game.KingGame, )
        for module in mods:
            module.servers = self.servers
            for func_name in get_module_events(module()):
                func = getattr(module(), func_name)
                setattr(self, func_name, func)

        try:
            event = ujson.loads(self.line)
        except ValueError:
            print("ERROR: Worker could not parse log line: %s" % self.line)
            raise

        try:            
            method = getattr(self, event['type'])
        except AttributeError as e:
            #print(e)
            #
            #NOT IMPLEMENTED!!!!!
            #
            return
        
        method(event, self.init, self.thread_lock)



class Main(object):
    logger = Logger.with_default_handlers(name='pyaltitude.Main')
    

    def run(self):
        self.servers = self.parse_server_config()
        self.queue = queue.Queue()
        self.thread_lock = Lock()

        ##################
        # NOTE
        #
        # parse config here and pass in
        # also determine which modules to load 
        # and pass in through to workers

        
        tail_thread=threading.Thread(target=self.tail, daemon=True)
        tail_thread.start()


        with concurrent.futures.ThreadPoolExecutor(min(32, os.cpu_count() + 4), thread_name_prefix='Worker-') as pool:
            # one NOTE is that I dont want to have to load modules
            # on every event worry about that later
            
            while True:
                try:
                    (line, INIT) = self.queue.get()
                    #print('Submitting Worker for line: %s' % line.strip())
                    worker = Worker(line, INIT, self.servers, self.thread_lock)
                    future = pool.submit(worker.execute)
                    future.add_done_callback(self.worker_done_cb)
                    time.sleep(.01)
                except KeyboardInterrupt:
                    #when hitting Ctrl-C
                    break


    def worker_done_cb(self, fut):
        exception = fut.exception()
        if exception:
            print('Worker exception (callback): %s' % repr(exception))
            try:
                #get the result so we raise the exception
                # and get the traceback
                fut.result()
            except Exception as e:
                print(traceback.format_exc())


    def tail(self):
        #seek to end of file and begin tailing
        with open(PATH, 'rt') as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.01)
                    continue
                self.queue.put((line, False))


    def parse_server_config(self):
        servers = dict()
        with open(LAUNCHER_CONFIG, 'rt') as f:
            contents = f.read()

        root = ET.fromstring(contents)
        for server_config in root.iter("AltitudeServerConfig"):
            server = Server()
            server = server.parse(server_config.attrib)
            #attrs = server.describe()
            servers[server.port] = server

        mapList = root.find('mapList')
        return servers
 

if __name__ == "__main__":
    #asyncio.run(Main().run())#, debug=True)
    Main().run()
