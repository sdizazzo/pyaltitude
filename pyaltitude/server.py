import uuid, time
import math
import subprocess, logging
from collections import namedtuple

from . import base
from . import commands


COMMAND_PATH = '/home/sean/altitude/servers/command.txt'


MockMap = namedtuple('MockMap', ('state', 'name'), defaults = (None, None))

logger = logging.getLogger(__name__)

class ServerLauncher(base.Base):
    servers = list()

    def server_for_port(self, port):
        for server in self.servers:
            if server.port == port:
                return server

    def parse(self, attrs):
        super().parse(attrs, convert_types=True)
        logger.info('Initialilzed ServerLauncher with IP %s' % (self.ip))
        return self


class Server(base.Base, commands.Commands):

    def __init__(self):
        # check if player is admin when logging in, then set is_admin
        self.admin_vaporIds = list()
        self.players = list() # <--- on active map??


        #self.teams = set() # server.map.leftteam, rightteam
        self.mapList = list() # can these be added to dynamically? check commands
        self.mapRotationList = list()

        self.map = MockMap()


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
        # This does execute on one worker thread, but splitting it up further
        # would be a challenge

        for pid, coords in event['positionByPlayer'].items():
            player = self.get_player_by_number(int(pid), bots=True)
            x, y, angle = coords.split(',')

            # calculate a simple velocity
            if player.is_alive() and all((player.x, player.y, player.angle, player.time)):

                # This should fix the ZeroDivisionError errors
                # Still seems weird that the server is sending events
                # with the same tick.
                # I guess I'm sending too many requests...?
                if now == player.time:
                    logger.warning("Skipping velocity event for %s as time had not changed.  Time: %s" %  (player.nickname, now))
                    #NOTE@@
                    # is this lag??
                    # Can I get the ping and report it when this happens?
                    # at first look I dont see a way.
                    continue

                distance = self.calc_distance(player.x, int(x), player.y, int(y))
                elapsed = now - player.time
                player.velocity = distance/elapsed

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
 
