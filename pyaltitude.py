#!/usr/bin/env python3.7

import asyncio
import aiofiles
import ujson
import uuid
import xml.etree.ElementTree as ET

#from threading import Thread

import logging
from aiologger import Logger
logging.basicConfig(level=logging.DEBUG)

import pprint
pp = pprint.PrettyPrinter(indent=4)

PATH = '/home/sean/altitude/servers/log.txt'
COMMAND_PATH = '/home/sean/altitude/servers/command.txt'
LAUNCHER_CONFIG = '/home/sean/altitude/servers/launcher_config.xml'


import commands
from modules import *

class Item(object):
    logger = Logger.with_default_handlers(name='pyaltitude.Item')

    """
        Objects subclass from this and json responses will be populated as
        instance variables automatically after calling 
        `await super().parse(attrs)`

        No boilerplate!
    """
    async def parse(self, json_dict, convert_types=False):
        for k, v in json_dict.items():
            if convert_types:
                v = await self.convert_value(v)
            setattr(self, k, v)

    async def convert_value(self, v):
        if v == 'true':
            return True
        elif v == 'false':
            return False
        elif v.isalnum():
            return int(v)
        return v

    async def describe(self):
        return pp.pformat({k:v for k,v in self.__dict__.items() if k != '_json'})

#class BotConfig(

class Server(Item, commands.Commands):
    logger = Logger.with_default_handlers(name='pyaltitude.Server')

    def __init__(self):
        # check if player is admin when logging in, then set is_admin
        self.admin_vaporIds = list()
        self.players = list() # <--- on active map??
        #self.teams = set() # server.map.leftteam, rightteam
        self.mapList = list() # can these be added to dynamically? check commands
        self.mapRotationList = list()
        

        self.active_map = None

    # NOTE
    # Load and Unload module methods have to be on the worker threads since
    # they executre in their own environment
    # I'm 90% sure

    async def set_active_map(self, map):
        print('Setting active_map on server %s to %s' % (self.serverName, map.name))
        self.active_map = map
            
    async def add_player(self, player, message=True):
        print('Adding player to server %s with %s' % (self.serverName, player.vaporId))
        self.players.append(player)
        await self.players_changed(player, True, message=message)

    async def remove_player(self, player, message=True):
        print('Removing player from server %s with %s' % (self.serverName, player.vaporId))
        self.players.remove(player)
        await self.players_changed(player, False, message=message)


    async def players_changed(self, player, added, message=True):
        if not player.is_bot():
            if added:
                print("%s joined server %s" % (player.nickname, self.serverName))
                await player.whisper('Hey %s!' % player.nickname)
                await player.whisper('Welcome to %s!' % self.serverName)

            if message:
                await self.serverMessage('%s players now in server' % len(self.get_players())) 
            print([p.nickname for p in self.get_players()])


    async def map_player_positions(self, event):
        #{"positionByPlayer":{"0":"776,726","1":"3028,683","2":"704,784","3":"3043,799","4":"652,733","5":"3095,748","6":"-1,-1"},"port":27278,"time":46699,"type":"logPlanePositions"}
        for pid, coords in event['positionByPlayer'].items():
            player = await self.get_player_by_number(int(pid), bots=False) 
            x, y = coords.split(',')
            if not player:
                continue
            player.x, player.y = (int(x), int(y))

    #async def message(self, message):
    #    await commands.ServerMessage(self.port, message).send()

    def get_players(self, bots=False):
        pl = list()
        for p in self.players:
            if not bots and p.is_bot():
                continue
            pl.append(p)
        return pl

    def get_players_by_team(self):
        teams = dict(leftTeam=list(), rightTeam=list())
        for p in self.get_players(bots=True):
            if p.team == self.active_map.leftTeam:
                teams['leftTeam'].append(p)
            elif p.team == self.active_map.rightTeam:
                teams['rightTeam'].append(p)
        return teams

    def get_player_by_vaporId(self, vaporId):
        for p in self.get_players():
            if p.vaporId == uuid.UUID(vaporId):
                return p
        #try:
        #    return next((p for p in self.players if p.vaporId == uuid.UUID(vaporId)))
        #except StopIteration:
        #    #slow, but don't think this raised often.  Only on startup
        #    return None

    async def get_player_by_number(self, number, bots=True):
        for p in self.get_players(bots=bots):
            #print(await p.describe())
            if p.player == number:
                return p

    async def parse(self, attrs):
        #convert_types since we are reading from the xml file
        await super().parse(attrs, convert_types=True)
        commands.Commands.__init__(self)        
        return self


class Map(Item):
    logger = Logger.with_default_handlers(name='pyaltitude.Map')

    def __init__(self, server):
        self.server = server

    async def parse(self, json):
        self._json = json
        await super().parse(json)

        self.name = self.map

        return self

    

class Team(object):
    pass


class Player(Item):
    logger = Logger.with_default_handlers(name='pyaltitude.Player')

    def __init__(self, server):
        self.is_admin = False
        self.server = server
        self.x = -1
        self.y = -1
        self.team = None
        #{"powerup":"Ball","positionY":1050,"playerVelX":-4.4,"playerVelY":-3.7,"port":27278,"velocityX":0,"time":389501,"type":"powerupPickup","velocityY":0,"player":2,"positionX":2036}
        #{"powerup":"Ball","positionY":158.65,"port":27278,"velocityX":-4.41,"time":1054454,"type":"powerupUse","velocityY":3.65,"player":4,"positionX":1191.59}
        self.powerup = None

    async def parse(self, json):
        self._json = json
        await super().parse(json)
        self.vaporId = uuid.UUID(self.vaporId)
        # UNTESTED
        #if self.vaporId in self.server.admin_vaporIds:
        #    self.is_admin = True
        return self

    async def parse_playerInfoEv(self, json):
        for k, v in json.items():
            if not k in ('port', 'type', 'player'):
                setattr(self, k, v)

    def set_team(self, team):
        self.team = team

    async def whisper(self, message):
        await self.server.serverWhisper(self.nickname, message)

    async def applyForce(self, x, y):
        await self.server.applyForce(self.player, x, y)


    def is_bot(self):
        return int(self.vaporId) == 0 

    def __eq__(self, other):
        return self.nickname == other.nickname
        #return self.vaporId == other.vaporId # what about bots?


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
        player = server.get_player_by_vaporId(event['vaporId'])
        if player:
            await server.remove_player(player, message=not INIT)


    async def logPlanePositions(self, event, _, servers):
        server = servers[event['port']]
        await server.map_player_positions(event)

    async def mapLoading(self, event, _,servers):
        server = servers[event['port']]
        print("MapLoading: %s" % event)


    async def mapChange(self, event, _, servers):
        server = servers[event['port']]
        #{"mode":"ball","rightTeam":5,"port":27278,"leftTeam":6,"time":5808529,"type":"mapChange","map":"ball_cave"}
        map_ = Map(server)
        map_ = await map_.parse(event)
        #might need to call a method here instead
        #map_.loadModules

        await server.set_active_map(map_)


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
            from_player = await server.get_player_by_name(event['arguments']['player'])
            to_player = await server.get_player_by_name(event['arguments']['string'])
            #get the coords from 
            #overrideSpawnPoint x y angle would work, but you have to die then
            #wait to spawn, plus I only want it to last for one life then reset
            #back to normal and Im not sure how to set it back yet


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
