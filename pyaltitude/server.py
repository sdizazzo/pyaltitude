import uuid, time
import math
import queue
import logging
from threading import Lock, Thread
from collections import namedtuple

import concurrent.futures

from . import base
from . import commands

from pyaltitude.worker import Worker


logger = logging.getLogger(__name__)

MockMap = namedtuple('MockMap', ('state', 'name'), defaults = (None, None))


class ServerNameAdapter(logging.LoggerAdapter):
    # Add the serverName attribute to certain log entries
    def process(self, msg, kwargs):
        return '%s - %s' % (self.extra['server'], msg), kwargs


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

    def __init__(self, config):
        self.config = config
        self.queue = queue.Queue()
        self.thread_lock = Lock()

        # check if player is admin when logging in, then set is_admin
        self.admin_vaporIds = list()
        self.players = list() # <--- on active map??


        #self.teams = set() # server.map.leftteam, rightteam
        self.mapList = list() # can these be added to dynamically? check commands
        self.mapRotationList = list()

        self.map = MockMap()


    def worker_done_cb(self, fut):
        exception = fut.exception()
        if exception:
            try:
                fut.result()
            except Exception as e:
                self.log_serverName.exception('Worker raised exception: %s' % repr(e))


    def run_thread_pool(self, workers):
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=workers)

        #Pass in the modules we want to load
        while True:
            line = self.queue.get()
            worker = Worker(line, self.config, self.thread_lock)
            future = pool.submit(worker.execute)
            future.add_done_callback(self.worker_done_cb)
            time.sleep(.01)

        pool.shutdown(wait=False)


    def run_thread_pool_thread(self, workers):
        #LOLOLOL
        logger.info('Initialized thread pool for server: %s with %s workers' % (self.serverName, workers))
        self.thread_pool_thread = Thread(target=self.run_thread_pool, args=(workers, ), daemon=True)
        self.thread_pool_thread.start()


    def add_player(self, player, message=True):
        logger.info('Adding player %s to server %s' % (player.nickname, self.serverName))
        self.players.append(player)
        self.players_changed(player, True)
        #logger.debug(player.describe())


    def remove_player(self, player, reason, explain):
        logger.info('Removing player %s from server %s, Reason: %s, Explain: %s' % (player.nickname, self.serverName, reason, explain))
        self.players.remove(player)
        self.players_changed(player, False)


    def players_changed(self, player, added):
        if not player.is_bot():
            if added:
                player.whisper('Hey %s!' % player.nickname)
                player.whisper('Welcome to %s!' % self.serverName)
                player_count = len(self.get_players())
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
                    self.log_serverName.warning("Skipping velocity event for %s as time had not changed.  Time: %s" %  (player.nickname, now))
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
        self.log_serverName = ServerNameAdapter(logger, {'server': self.serverName})
        # TODO
        # get the number of workers fromo the config file!
        self.run_thread_pool_thread(5)
        commands.Commands.__init__(self, self.config)
        return self
 
