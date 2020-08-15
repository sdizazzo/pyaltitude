import os, uuid, time
import math
import queue
import logging
import importlib
import subprocess

from signal import SIGTERM
from threading import Lock, Thread
from collections import namedtuple

import concurrent.futures

from . import base
from . import commands

import pyaltitude.db as database

from pyaltitude.worker import Worker


logger = logging.getLogger(__name__)

MockMap = namedtuple('MockMap', ('state', 'name'), defaults = (None, None))


class ServerNameAdapter(logging.LoggerAdapter):
    # Add the serverName attribute to certain log entries
    def process(self, msg, kwargs):
        return '%s - %s' % (self.extra['server'], msg), kwargs


class ServerManager(base.Base):
    servers = list()

    """
        #
        # server_launcher command line options!
        # I figued it was a hidden gem, and if I didnt
        # keep a record, nobody would ever see it again!
        #
           -ip X
           -updatePort X
           -gamePorts X,Y,Z
           -maxPlayers X,Y,Z
           -downloadMaxKilobytesPerSecond X,Y,Z
        Example for 1 instance: ./server_launcher -ip 192.168.1.3 -updatePort 40000 -gamePorts 40001 -maxPlayers 14 -downloadMaxKilobytesPerSecond 40
        Example for 3 instances: ./server_launcher -ip 192.168.1.3 -updatePort 40000 -gamePorts 40001,40002,40003 -maxPlayers 8,14,14 -downloadMaxKilobytesPerSecond 40,80,80

        Other options:
           -noui            disables graphical user interface in non-headless environments

    """


    def server_for_port(self, port):
        for server in self.servers:
            if server.port == port:
                return server


    def broadcast_msg(self, msg):
        logger.info("broadcasting message to all servers: '%s'" % msg)
        for server in self.servers:
           server.serverMessage(msg)


    def get_java_pid(self):
        cp = subprocess.run(['ps', '-ef'],
                            capture_output=True,
                            check=True,
                            universal_newlines=True
                            )


        for pline in cp.stdout.split('\n'):
            if all(p in pline for p in ('java', 'server_launcher')):
                return int(pline.split()[1])


    def shutdown_java_server(self):
        pid = self.get_java_pid()
        if not pid:
            raise ValueError('Could not determine determine pid for altitude server.  Is it running?')

        os.kill(pid, SIGTERM)


    def shutdown(self, alti_server=True):
        for server in self.servers:
            logger.info('Shutting down %s' % server.serverName)
            server.shutdown()

        if alti_server:
            logger.info('Shutting down Altitude server')
            self.shutdown_java_server()


    def servers_with_players(self):
        servers = []
        for server in self.servers:
            if server.get_players():
                servers.append(server)
        return servers


    def parse(self, attrs):
        super().parse(attrs, convert_types=True)
        logger.info('Initialilzed ServerLauncher with IP %s' % (self.ip))
        return self


class Server(base.Base, commands.Commands):

    def __init__(self, config):
        self.config = config
        self.queue = queue.Queue()

        self.game = None

        # check if player is admin when logging in, then set is_admin
        self.admin_vaporIds = list()
        self.players = list() # <--- on active map??


        #self.mapList = list() # can these be added to dynamically? check commands
        #self.mapRotationList = list()

        # set dynamically from yaml file
        # see config_from_yaml() passed from config.py
        self.modules = list()

        #scoped_session - thread local scope
        self.session = self.config.Session()


    def shutdown(self):
        #TODO do I even need to do `get_players() anymore?
        for player in self.get_players():
            logger.warning("Dropping %s from %s" % (player.nickname, self.serverName))
            self.serverMessage("Dropping %s from %s"  % (player.nickname, self.serverName))
            self.drop(player)
            time.sleep(.2)
            # NOTE since drop() is called before the removeClient
            # it appears the database is never updated  that the client was
            # dropped. SO lets call it manually
            # dropped. SO lets call it manually
            # is this the "correct" solution?  I'm not sure, but it seems the
            # best ATM

            # Send a mock the event with only the needed field
            database.client_remove(player, self, {'reason':'Dropped by server admin'})


    def run_worker_thread(self, queue):
        while True:
            line = queue.get()
            worker = Worker(line, self.config, modules=self.modules)
            worker.execute()


    def start_worker_thread(self):
        logger.info('Initialized worker thread for server: %s' % self.serverName)
        self.worker_thread = Thread(target=self.run_worker_thread, args=(self.queue, ), daemon=True)
        self.worker_thread.start()


    def add_player(self, player, message=True):
        logger.info('Adding player %s to server %s, message: %s' % (player.nickname, self.serverName, message))
        self.players.append(player)
        self.players_changed(player, True)
        #logger.debug(player.describe())


    def remove_player(self, player, reason, explain):
        logger.info('Removing player %s from server %s, Reason: %s, Explain: %s' % (player.nickname, self.serverName, reason, explain))
        self.players.remove(player)
        self.players_changed(player, False)


    def whisper_all(self, message):
        for player in self.get_players():
            player.whisper(message)


    def players_changed(self, player, added):
        if not player.is_bot():
            if added:
                player.whisper('Hey %s!' % player.nickname)
                player.whisper('Welcome to %s!' % self.serverName)
                player.whisper('Simple stat tracking is now active at http://216.70.113.96:5000/')
                player.whisper('Super basic, but perhaps something better will grow from it in time.')
                #player.whisper('grow from it in time.')


            players = self.get_players()

            self.serverMessage("Players now in server: %s" % len(players))
            logger.info("Players now in %s: %s" % (self.serverName, [p.nickname for p in players]))


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
                    self.log_serverName.debug("Skipping velocity event for %s as time had not changed.  Time: %s" %  (player.nickname, now))
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
            if p.player == number:
                return p

            
    def get_player_by_name(self, name):
        for p in self.get_players():
            if p.nickname == name:
                return p


    def config_from_yaml(self, conf):
        for k, v in conf.items():
            #special case for `modules` key in yaml
            if k and k == 'modules':
                mods = list()
                if v:
                    for module in v:
                        #import the server modules
                        mod_name, mod_class = module.split('.')
                        mod = importlib.import_module('.modules.'+ mod_name, package='pyaltitude')
                        klass = getattr(mod, mod_class)
                        mods.append(klass)
                    v = mods
            if v:
                self.log_serverName.info("Setting server attr from yaml config: %s => %s" % (k, v))
                setattr(self, k, v)


    def parse(self, attrs):
        #convert_types since we are reading from the xml file
        super().parse(attrs, convert_types=True)
        logger.info('Initialilzed server: %s on port %s' % (self.serverName, self.port))
        self.log_serverName = ServerNameAdapter(logger, {'server': self.serverName})
        commands.Commands.__init__(self, self.config)
        return self
 
