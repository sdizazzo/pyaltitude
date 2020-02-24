import uuid, time
import math
import subprocess, logging
from collections import namedtuple
from threading import Thread, Event

from . import base
from . import commands


COMMAND_PATH = '/home/sean/altitude/servers/command.txt'


MockMap = namedtuple('MockMap', ('state', 'name'), defaults = (None, None))

logger = logging.getLogger(__name__)

class Server(base.Base, commands.Commands):

    def __init__(self):
        # check if player is admin when logging in, then set is_admin
        self.admin_vaporIds = list()
        self.players = list() # <--- on active map??


        #self.teams = set() # server.map.leftteam, rightteam
        self.mapList = list() # can these be added to dynamically? check commands
        self.mapRotationList = list()

        self.map = MockMap()

        self.log_planes_thread = None
        self.log_planes_event = Event()


    def log_planes(self, event):
        this_cmd = "%s,console,logPlanePositions" % self.port
        cmd = '/bin/echo "%s" >> %s' % (this_cmd, COMMAND_PATH)
        while 1:
            if event.is_set():
                break
            subprocess.run(cmd, shell=True)
            time.sleep(.1)


    def add_player(self, player, message=True):
        logger.info('Adding player %s to server %s' % (player.nickname, self.serverName))
        self.players.append(player)
        self.players_changed(player, True, message=message)
        #logger.debug(player.describe())


    def remove_player(self, player, reason, explain, message=True):
        logger.info('Removing player %s from server %s, Reason: %s, Explain: %s' % (player.nickname, self.serverName, reason, explain))
        self.players.remove(player)
        self.players_changed(player, False, message=message)

    def players_changed(self, player, added, message=True):
        if not player.is_bot():
            if added:
                player.whisper('Hey %s!' % player.nickname)
                player.whisper('Welcome to %s!' % self.serverName)

            player_count = len(self.get_players())
            #
            #TODO HACK!!!
            #
            # only log plane positions on King of the Hill
            if self.port in (27282, 27283) and player_count == 1 and not self.log_planes_thread:
                #when the first player enters the arena, start the log planes thread
                logger.info('Starting log plane thread on %s' % self.serverName)
                self.log_planes_thread = Thread(target=self.log_planes, args=(self.log_planes_event, ),daemon=True)
                self.log_planes_thread.start()
    
            #
            # TODO HACK!!!!
            #
            elif self.port in (27282, 27283) and player_count == 0:
                # last player leaves, stop it
                logger.info('Stopping log plane thread on %s' % self.serverName)
                self.log_planes_event.set()
                time.sleep(1)
                self.log_planes_thread = None
                self.log_planes_event = Event()

            if message:
                self.serverMessage('%s players now in server' % player_count)
            logger.info("Players now in %s: %s" % (self.serverName, [p.nickname for p in self.get_players()]))


    #will go into some kind of utils or math module
    def calc_distance(self, x1, y1, x2, y2):
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2) 


    def map_player_positions(self, event):
        now = event['time']

        #
        # Now that we are doing some actual calculations and things that could
        # throw errors it would be much better to break this up per player and 
        # execute this on the worker threads.  Not sure how feasible that is 
        # since it's not an event.
        #
        for pid, coords in event['positionByPlayer'].items():
            player = self.get_player_by_number(int(pid), bots=True)
            x, y, angle = coords.split(',')

            # calculate a simple velocity
            if player.is_alive() and all((player.x, player.y, player.angle, player.time)):
                distance = self.calc_distance(player.x, int(x), player.y, int(y))
                elapsed = now - player.time
                # hmmmm....
                # got a ZeroDivisionError here
                # not convinced yet. Its late.
                player.velocity = distance/elapsed
                logger.debug("Set player velocity: %s" % player.velocity)

            player.x, player.y, player.angle, player.time = (int(x), int(y), int(angle), now)


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
            if p.team == self.map.leftTeam:
                teams['leftTeam'].append(p)
            elif p.team == self.map.rightTeam:
                teams['rightTeam'].append(p)
        return teams


    def get_player_by_vaporId(self, vaporId):
        for p in self.get_players():
            if p.vaporId == uuid.UUID(vaporId):
                return p


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
        logger.info('Initialilzed server: %s on port %s' % (self.serverName, self.port))
        commands.Commands.__init__(self)
        return self
 
