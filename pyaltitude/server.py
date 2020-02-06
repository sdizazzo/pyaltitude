import uuid,time
import aiofiles
from threading import Thread, Event

import subprocess

from . import base
from . import commands

from aiologger import Logger

COMMAND_PATH = '/home/sean/altitude/servers/command.txt'

class Server(base.Base, commands.Commands):
    logger = Logger.with_default_handlers(name='pyaltitude.Server')

    def __init__(self):
        # check if player is admin when logging in, then set is_admin
        self.admin_vaporIds = list()
        self.players = list() # <--- on active map??


        #self.teams = set() # server.map.leftteam, rightteam
        self.mapList = list() # can these be added to dynamically? check commands
        self.mapRotationList = list()

        self.map = None

        self.log_planes_thread = None
        self.log_planes_event = Event()


    def log_planes(self, event):
        this_cmd = "%s,console,logPlanePositions" % self.port
        cmd = '/bin/echo "%s" >> %s' % (this_cmd, COMMAND_PATH)
        while 1:
            if event.is_set():
                break
            subprocess.run(cmd, shell=True)
            time.sleep(.5)

    # NOTE
    # Load and Unload module methods have to be on the worker threads since
    # they executre in their own environment
    # I'm 90% sure
    def set_map(self, map):
        #TODO I don't believe we need this method
        print('Setting map on server %s to %s' % (self.serverName, map.name))
        self.map = map

    def add_player(self, player, message=True):
        print('Adding player %s to server %s' % (player.nickname, self.serverName))
        self.players.append(player)
        self.players_changed(player, True, message=message)

    def remove_player(self, player, message=True):
        print('Removing player %s from server %s' % (player.nickname, self.serverName))
        self.players.remove(player)
        self.players_changed(player, False, message=message)

    def players_changed(self, player, added, message=True):
        if not player.is_bot():
            if added:
                print("%s joined server %s" % (player.nickname, self.serverName))
                player.whisper('Hey %s!' % player.nickname)
                player.whisper('Welcome to %s!' % self.serverName)

            player_count = len(self.get_players())
            if player_count == 1 and not self.log_planes_thread:
                #when the first player enters the arena, start the log planes thread
                print('Starting log plane thread on %s' % self.serverName)
                self.log_planes_thread = Thread(target=self.log_planes, args=(self.log_planes_event, ),daemon=True)
                self.log_planes_thread.start()
    
            elif player_count == 0:
                # last player leaves, stop it
                print('Stopping log plane thread on %s' % self.serverName)
                self.log_planes_event.set()
                time.sleep(1)
                self.log_planes_thread = None
                self.log_planes_event = Event()

            if message:
                self.serverMessage('%s players now in server' % player_count)
            print([p.nickname for p in self.get_players()])


    def map_player_positions(self, event):
        #{"positionByPlayer":{"0":"776,726","1":"3028,683","2":"704,784","3":"3043,799","4":"652,733","5":"3095,748","6":"-1,-1"},"port":27278,"time":46699,"type":"logPlanePositions"}
        for pid, coords in event['positionByPlayer'].items():
            player = self.get_player_by_number(int(pid), bots=False)
            x, y = coords.split(',')
            if not player:
                continue
            player.x, player.y = (int(x), int(y))

    def get_players(self, bots=False):
        pl = list()
        for p in self.players:
            if not bots  and p.is_bot():
                continue
            pl.append(p)
        return pl

    def get_players_by_team(self):
        teams = dict(leftTeam=list(), rightTeam=list())
        for p in self.get_players(bots=True):
            if p.team == self.map.leftTeam:
                teams['leftTeam'].append(p)
            elif p.team == self.map.rightTeam:
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

    def get_player_by_number(self, number, bots=True):
        for p in self.get_players(bots=bots):
            #print(p.describe())

            if p.player == number:
                return p

    def get_player_by_name(self, name):
        for p in self.get_players():
            if p.nickname == name:
                return p

    def parse(self, attrs):
        #convert_types since we are reading from the xml file
        super().parse(attrs, convert_types=True)
        commands.Commands.__init__(self)
        return self
 
