#!/usr/bin/env python3.7

import asyncio
import aiofiles
import ujson
import xml.etree.ElementTree as ET
import concurrent.futures
import queue
import time
import logging
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
from pyaltitude.map import Map
from pyaltitude.enums import MapState
from pyaltitude.player import Player
from pyaltitude.server import Server
from pyaltitude.modules import *
#from pyaltitude.custom_commands import attach

class Events(object):
    logger = Logger.with_default_handlers(name='pyaltitude.Events')

    def clientAdd(self, event, INIT, servers):
        server = servers[event['port']]
        player = Player(server)
        player = player.parse(event)
        server.add_player(player, message =not INIT)


    def clientRemove(self, event, INIT,servers):
        #get the server first, and then the player from that
        server = servers[event['port']]
        #NOTE 
        # BUG player is None sometimes here and I dont understand why yet
        #Its a race condition.  Not sure if it matters or not yet
        # seems not to so I'll leave it as is for now and worry later
        player = server.get_player_by_vaporId(event['vaporId'])
        if player:
            server.remove_player(player, message =not INIT)

    def spawn(self, event, _, servers):
        server = servers[event['port']]
        #{'plane': 'Biplane', 'port': 27280, 'perkGreen': 'Heavy Armor',
        #'perkRed': 'Heavy Cannon', 'skin': 'No Skin', 'team': 4, 'time':
        #18018150, 'type': 'spawn', 'perkBlue': 'Ultracapacitor', 'player': 2}
        player = server.get_player_by_number(event['player'])
        if player:
            player.spawned()


    def logPlanePositions(self, event, _, servers):
        server = servers[event['port']]
        server.map_player_positions(event)


    def mapLoading(self, event, _,servers):
        server = servers[event['port']]
        print("MapLoading: %s" % event)
        #{'port': 27279, 'time': 16501201, 'type': 'mapLoading', 'map':'ffa_core'}
        # THis event gives us the map name which is enough to
        # instatiate the map object and begin parsing the map 
        # file for what we need:
        #    * right now just the spawn points so we can reset to them
        #      after an /attach to a player
        map_ = Map(server, event['map'])
        map_.parse_alte()
        server.map = map_


    def mapChange(self, event, _, servers):
        server = servers[event['port']]
        #{"mode":"ball","rightTeam":5,"port":27278,"leftTeam":6,"time":5808529,"type":"mapChange","map":"ball_cave"}
        print("MapChange: %s" % event)

        #NOTE since we are essentially parsing/instantiating the Map object
        #twice with two different sets of data, I worry a little that some 
        #attributes might be overwritten.  Keep it on the radar

        wait = .1
        t = 0
        while not server.map.state == MapState.READY:
            time.sleep(wait)
            #await asyncio.sleep(wait)
            print('WARNING!!!! sleeping waiting for map to become available')
            t+=wait
            if t > 2:
                print('WARNING!!!!!! Took over 2 seconds to parse map.  Continued anyway...')
                break
        server.map.parse(event)
        server.map.state = MapState.ACTIVE


    def playerInfoEv(self, event, _, servers):
        server = servers[event['port']]
        #    #{"plane":"Loopy","level":1,"port":27278,"perkGreen":"No Green Perk","perkRed":"Tracker","team":2,"time":5808868,"type":"playerInfoEv","leaving":false,"perkBlue":"No Blue Perk","aceRank":0,"player":1}
        #print("playerInfoEv: %s" % event)
        player = server.get_player_by_number(event['player'])
        if player:
            player.parse_playerInfoEv(event)
            

    def teamChange(self, event, _, servers):
        server = servers[event['port']]
        #{"port":27278,"team":2,"time":5808868,"type":"teamChange","player":0}
        player = server.get_player_by_number(event['player'])
        #print("Set team: %s" % event)
        if player:
            player.set_team(event['team'])
        
    def attach(self, server,from_player, to_player):
        if from_player.team and from_player.team == 2:
            from_player.whisper("Can't attach from spec")
            return
        if to_player.team and to_player.team == 2:
            from_player.whisper("Can't attach to a player in spec")
            return
        if not to_player.is_alive():
            from_player.whisper("Can't attach. %s is dead!" % to_player.nickname)
            return
        if from_player.attached:
            from_player.whisper("You've already attached once this life!")
            return

        #if from_player == to_player:
        #    from_player.whisper('Not a chance!!')
        #    return
        #elif not from_player.team == to_player.team:
        #    from_player.whisper('You can only attach to members of your own team!')
        #    return
        from_player.whisper('Attaching to %s' % to_player.nickname)
        to_player.whisper('%s is attaching to you!' % from_player.nickname)
        server.overrideSpawnPoint(from_player.nickname, to_player.x, to_player.y, 0)
        from_player.attached = True



    def consoleCommandExecute(self, event, _, servers):
        #TODO Need to see if server (below) can be factored in to the init
        #method
        server = servers[event['port']]

        #
        # Custom commands - More shit to do!!!
        #
        # TODO Needs to be broken out into its own piece
        #
        from_player = None
        to_player = None
        if event['command'] in ( 'a', 'attach'):
            #print('THE EVENT', event)
            from_player = server.get_player_by_vaporId(event['source'])
            if event['command'] == 'a':
                to_player = from_player.last_attached_player
                if not to_player:
                    from_player.whisper("You haven't attached to anybody yet")
                    return
            else:
                to_player = server.get_player_by_name(event['arguments'][0])
                from_player.last_attached_player = to_player
        
            self.attach(server, from_player, to_player)


        #command needs to be called dynamilcally instead
        #Similarlly to modules
        #THis is adding too much complexity for this week
        ##TODO for when I am
        #    command = Attach(server, from_player, to_player)
        #    command.execute()
            

class Worker(Events):
    logger = Logger.with_default_handlers(name='pyaltitude.Worker')

    def __init__(self, queue, servers):
        self.queue = queue
        self.servers = servers

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
        mods = (shockwave.ShockWaveModule, )
        for module in mods:
            for func_name in get_module_events(module()):
                func = getattr(module(), func_name)
                setattr(self, func_name, func)
        (line, INIT) = self.queue.get()
        event = ujson.loads(line)
        try:            
            method = getattr(self, event['type'])
        except AttributeError as e:
            #print(e)
            #
            #NOT IMPLEMENTED!!!!!
            #
            return
        method(event, INIT, self.servers)           
        self.queue.task_done()
                


class Main(object):
    logger = Logger.with_default_handlers(name='pyaltitude.Main')

    async def run(self):
        self.servers = self.parse_server_config()
        self.queue = queue.Queue()
     
        ##################
        # NOTE
        #
        # parse config here and pass in
        # also determine which modules to load 
        # and pass in through to workers

        loop = asyncio.get_running_loop()

        tail_thread=threading.Thread(target=self.tail, daemon=True)
        tail_thread.start()

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            # There is no worker concept with an endless loop.
            # the pool takes care of that for us
            # we just have a class/function that pulls from the 
            # queue and executes code against that event
            #
            # one NOTE is that I dont want to have to load modules
            # on every event worry about that later
            while True:
                worker = Worker(self.queue, self.servers)
                result = await loop.run_in_executor(pool, worker.execute)
                #print(result.result())
                await asyncio.sleep(.1)



    def tail(self):
        #seek to end of file and begin tailing
        with open(PATH, 'rt') as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.1)
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
    asyncio.run(Main().run())#, debug=True)
