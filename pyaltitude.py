#!/usr/bin/env python3.7

import asyncio
import aiofiles
import ujson
import xml.etree.ElementTree as ET

import logging
from aiologger import Logger
logging.basicConfig(level=logging.DEBUG)

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


class Events(object):
    logger = Logger.with_default_handlers(name='pyaltitude.Events')

    async def clientAdd(self, event, INIT, servers):
        server = servers[event['port']]
        player = Player(server)
        player = await player.parse(event)
        await server.add_player(player, message=not INIT)


    async def clientRemove(self, event, INIT,servers):
        #get the server first, and then the player from that
        server = servers[event['port']]
        #NOTE 
        # BUG player is None sometimes here and I dont understand why yet
        #Its a race condition.  Not sure if it matters or not yet
        # seems not to so I'll leave it as is for now and worry later
        player = await server.get_player_by_vaporId(event['vaporId'])
        if player:
            await server.remove_player(player, message=not INIT)

    async def spawn(self, event, _, servers):
        server = servers[event['port']]
        #{'plane': 'Biplane', 'port': 27280, 'perkGreen': 'Heavy Armor',
        #'perkRed': 'Heavy Cannon', 'skin': 'No Skin', 'team': 4, 'time':
        #18018150, 'type': 'spawn', 'perkBlue': 'Ultracapacitor', 'player': 2}
        player = await server.get_player_by_number(event['player'])
        if player:
            await player.spawned()


    async def logPlanePositions(self, event, _, servers):
        server = servers[event['port']]
        await server.map_player_positions(event)

    async def mapLoading(self, event, _,servers):
        server = servers[event['port']]
        print("MapLoading: %s" % event)
        #{'port': 27279, 'time': 16501201, 'type': 'mapLoading', 'map':'ffa_core'}
        # THis event gives us the map name which is enough to
        # instatiate the map object and begin parsing the map 
        # file for what we need:
        #    * right now just the spawn points so we can reset to them
        #      after an /attach to a player
        map_ = Map(server, event['map'])
        await map_.parse_alte()
        server.map = map_


    async def mapChange(self, event, _, servers):
        server = servers[event['port']]
        #{"mode":"ball","rightTeam":5,"port":27278,"leftTeam":6,"time":5808529,"type":"mapChange","map":"ball_cave"}
        print("MapChange: %s" % event)

        #NOTE since we are essentially parsing/instantiating the Map object
        #twice with two different sets of data, I worry a little that some 
        #attributes might be overwritten.  Keep it on the radar

        wait = .1
        t = 0
        while not server.map.state == MapState.READY:
            await asyncio.sleep(wait)
            print('WARNING!!!! sleeping waiting for map to become available')
            t+=wait
            if t > 2:
                print('WARNING!!!!!! Took over 2 seconds to parse map.  Continued anyway...')
                break
        await server.map.parse(event)

        #might need to call a method here instead
        #map_.loadModules

        server.map.state = MapState.ACTIVE



    async def playerInfoEv(self, event, _, servers):
        server = servers[event['port']]
        #    #{"plane":"Loopy","level":1,"port":27278,"perkGreen":"No Green Perk","perkRed":"Tracker","team":2,"time":5808868,"type":"playerInfoEv","leaving":false,"perkBlue":"No Blue Perk","aceRank":0,"player":1}
        #print("playerInfoEv: %s" % event)
        player = await server.get_player_by_number(event['player'])
        if player:
            await player.parse_playerInfoEv(event)
            

    async def teamChange(self, event, _, servers):
        server = servers[event['port']]
        #{"port":27278,"team":2,"time":5808868,"type":"teamChange","player":0}
        player = await server.get_player_by_number(event['player'])
        #print("Set team: %s" % event)
        if player:
            player.set_team(event['team'])
        

    async def consoleCommandExecute(self, event, _, servers):
        #TODO Need to see if server (below) can be factored in to the init
        #method
        server = servers[event['port']]

        #
        # Custom commands - More shit to do!!!
        #
        # TODO Needs to be broken out into its own piece
        #
        if event['command'] == 'attach':
            from_player = await server.get_player_by_vaporId(event['source'])
            to_player = await server.get_player_by_name(event['arguments'][0])
            
            #after we have fun playing around with it, lock it down to same
            #team only
            #NOTE In some games we might also wnat to consider limiting attach
            # to only certain plane types
            if from_player.team and from_player.team == 2:
                await from_player.message("Can't attach from spec")
                return
            if to_player.team and to_player.team == 2:
                await from_player.whisper("Can't attach to a player in spec")
                return
            if not to_player.is_alive():
                await from_player.whisper("Can't attach. %s is dead!" % to_player.nickname)
                return
            if from_player.attached:
                await from_player.whisper("You've already attached once this life!")
                return

            #if from_player == to_player:
            #    await from_player.whisper('Not a chance!!')
            #    return
            #elif not from_player.team == to_player.team:
            #    from_player.whisper('You can only attach to members of your own team!')
            #    return
            await from_player.whisper('Attaching to %s' % to_player.nickname)
            await to_player.whisper('%s is attaching to you!' % from_player.nickname)
            await server.overrideSpawnPoint(from_player.nickname, to_player.x, to_player.y, 0)
            from_player.attached = True
            # pass x=0,y=0,angle=0 to clear the override and resume normal
            # spawning rules for a target player, otherwise overrides are
            # cleared on map change (after "mapLoading" but before "mapChange")
            # and on player disconnection
            
            #spawnPoint is reset with 'spawn' event


class Worker(Events):
    logger = Logger.with_default_handlers(name='pyaltitude.Worker')

    def __init__(self, queue, servers):
        self.queue = queue
        self.servers = servers
        self._worker = None

    def start(self):
        self._worker = asyncio.create_task(self._start(self.queue, self.servers))


    #
    # PASS IN THE MODULES HERE!!!
    #
    async def _start(self, queue, servers):
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

        while True:
            (line, INIT) = await self.queue.get()
            event = ujson.loads(line)
            try:            
                method = getattr(self, event['type'])
            except AttributeError as e:
                #print(e)
                #
                #NOT IMPLEMENTED!!!!!
                #
                continue
            await method(event, INIT, servers)           
            queue.task_done()
                


class WorkerManager(object):
    logger = Logger.with_default_handlers(name='pyaltitude.WorkerManager')

    def __init__(self, queue, servers, max_workers=10):
        self.queue = queue
        self.max_workers = 10
        self.servers = servers
        self.workers = set()
    
    def start_workers(self):
        for _ in range(self.max_workers):
            worker = Worker(self.queue, self.servers)
            worker.start()
            self.workers.add(worker)



#def start_loop(loop):
#    asynciojson['type'] ==.set_event_loop(loop)
#    loop.run_forever()
#    new_loop = asyncio.new_event_loop()
#         
#         t = Thread(target=start_loop, args=(new_loop,))
#         t.start()


class Main(object):
    logger = Logger.with_default_handlers(name='pyaltitude.Main')

    async def run(self):
        self.servers = await self.parse_server_config()
        self.queue = asyncio.Queue()
     
        ##################
        # NOTE
        #
        # parse config here and pass in
        # also determine which modules to load 
        # and pass in through to workers
        self.worker_manager = WorkerManager(self.queue, self.servers, max_workers=10)
        self.worker_manager.start_workers()

        await self.init()
        await self.tail()


    async def init(self):
        #only read until we get to EOF
        ignored_vaporIds = list()
        async with aiofiles.open(PATH) as f:
            for line in reversed(await f.readlines()):
                event = ujson.loads(line)
                #some crazy race conditions here!!!!
                if event['type'] in ('clientRemove', 'clientAdd'):
                    if event['vaporId'] in ignored_vaporIds and not event['nickname'].startswith('Bot'):
                        continue
                    if event['type'] == 'clientAdd':
                        await self.queue.put((line, True))
                    ignored_vaporIds.append(event['vaporId'])


    async def tail(self):
        #seek to end of file and begin tailing
        async with aiofiles.open(PATH) as f:
            await f.seek(0, 2)
            while True:
                line = await f.readline()
                if not line:
                    await asyncio.sleep(0.1)
                    continue
                await self.queue.put((line, False))



    async def parse_server_config(self):
        servers = dict()
        async with aiofiles.open(LAUNCHER_CONFIG) as f:
            contents = await f.read()

        root = ET.fromstring(contents)
        for server_config in root.iter("AltitudeServerConfig"):
            server = Server()
            server = await server.parse(server_config.attrib)
            #attrs = await server.describe()
            servers[server.port] = server

        mapList = root.find('mapList')
        return servers
 

if __name__ == "__main__":
    asyncio.run(Main().run())#, debug=True)
