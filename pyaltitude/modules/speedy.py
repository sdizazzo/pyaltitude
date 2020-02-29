import time
import math
import logging

from threading import Thread, Event

from . import module
from .. import events


logger = logging.getLogger(__name__)


"""
Fun module that tries to speed up the player by pushing them
along the same path they are flying.  There is some lag, so
it feels like you are sliding around on ice.  It's gotten a
decent response so far.  I call it Speed Ball.

"""

class SpeedyModule(module.ServerModule):

    def __init__(self, port=27283):
        self.port = port
        super().__init__(self, map)

    def _norm_angle(self, angle):
        #normalize the negative angles
        #cause its confusing!
        if angle < 0:
            return 360+angle
        return angle


    def _clamp(self, n, min_, max_):
        return max(min(max_, n), min_)


    def force_parallel_w_angle(self, angle, multiplier=3):
        # Im not practiced in math, but after some research,
        # this seems to get somewhat close for now.
        # The constant is arbitrary to make it work with
        # the multiplier

        # Thanks to WhetamP for helping me figure out that I
        # needed to pass radians to cos() and sin()!
        rads = angle * (math.pi/180)
        xforce = math.cos(rads)*1.2
        yforce = math.sin(rads)*1.2

        retx = self._clamp(int(xforce*multiplier), -15, 15)
        rety = self._clamp(int(yforce*multiplier), -15, 15)
        
        return retx, rety


    def be_speedy(self, server, player):
        logger.debug('Speedy thread started')
        player.whisper("3")
        time.sleep(1)
        player.whisper("2")
        time.sleep(1)
        player.whisper("1")
        time.sleep(1)
        player.whisper("Arriba Arriba!  Andale Arriba!  Yeppa!!")
        wait = .2
        while True:
            if player.game_event.is_set() or not player.is_alive():
                break

            normalized_angle = self._norm_angle(player.angle)
            forcex, forcey = self.force_parallel_w_angle(normalized_angle)
            logger.debug("Pushing %s for angle %s with x:%s, y:%s" %(player.nickname, normalized_angle, forcex, forcey))
            player.applyForce(forcex, forcey)
            time.sleep(wait)

        logger.debug('Speedy thread stopped')

    """
    TODO BUG!!! Inheriting the same event in multiple modules causes only the
    last to be honored.  Time for a refactor!  Opening an issue.

    def clientAdd(self, event, _, thread_lock):
        events.Events.clientAdd(self, event, _, thread_lock)
        server = self.servers[event['port']]
        if server.port !=  self.port: return

        player = server.get_player_by_number(event['player'])
        if not player.is_bot():
            logger.info("%s joined %s from %s" % (player.nickname, server.serverName, player.ip))
            player.whisper("*********************************************************************")
            player.whisper("In this arena, the ball carrier gets a speed boost of sorts.")
            player.whisper("It seems a bit slippery too, but you don't need to thrust to")
            player.whisper("move at high speed.  Still working out the details.")
            player.whisper("Highly experimental, but kind of neat.")
            player.whisper("Arriba Arriba!  Andale Arriba!  Yeppa!!")
            player.whisper("*********************************************************************")
    """

    def spawn(self, event, _, thread_lock):
        # NOTE If the module classes are subclassed properly, I think
        # I can make these calls to the event super method automatic
        # Relying on a user to mke them in every module event is error prone
        events.Events.spawn(self, event, _, thread_lock)

        server = self.servers[event['port']]
        if server.port !=  self.port: return

        player = server.get_player_by_number(event['player'])

        # Put the thread on the player itself!
        #much easier to track that way
        player.game_event.clear()
        player.game_thread = Thread(target=self.be_speedy, args=(server, player), daemon=True)
        player.game_thread.start()

