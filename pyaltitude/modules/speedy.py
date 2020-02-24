import time
import math
import logging

from threading import Thread, Event

from . import module
from .. import events


logger = logging.getLogger(__name__)


"""
Fun module that tries to speed up the player by pushing them
along the same angle they are flying (pointing) whenever they
are carrying the ball.

Might find use in some games as a powerup since you dont even
need to thrust to fly at high speed.  Or maybe a game where 
everybody is flying around like this.

COuld it be modified to allow the user to change the amount 
based on a key press?

"""

class SpeedyModule(module.MapModule):
    speedy_thread = None
    speedy_event = Event()

    def __init__(self, map='ball_football'):
        self.map = map
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
        for i in range(0, 360):
            if 0 < angle <= 90 or 270 < angle <= 360:
                xsign = 1
            else:
                xsign = -1

            if 0 < angle <= 180:
                ysign = 1
            else:
                ysign = -1

            if angle == i:
                # Im not practiced in math, but after some research,
                # this seems to get somewhat close for now.
                # The constant is arbitrary to make it work with
                # the multiplier
                xforce = abs(math.cos(angle))*1.3*xsign
                yforce = abs(math.sin(angle))*1.3*ysign
                break

        retx, rety = int(xforce*multiplier) , int(yforce*multiplier)
        
        retx = self._clamp(retx, -15, 15)
        rety = self._clamp(rety, -15, 15)

        return retx, rety


    def be_speedy(self, server, player, event):
        logger.debug('Speedy thread started')
        
        wait = .1
        while True:
            if event.is_set() or not player.is_alive():
                break

            normalized_angle = self._norm_angle(player.angle)
            forcex, forcey = self.force_parallel_w_angle(normalized_angle)
            logger.info("Pushing %s for angle %s with x:%s, y:%s" %(player.nickname, normalized_angle, forcex, forcey))
            player.applyForce(forcex, forcey)
            time.sleep(wait)

        logger.debug('Speedy thread stopped')


    def powerupPickup(self, event, _, thread_lock):
        # NOTE If the module classes are subclassed properly, I think
        # I can make these calls to the event super method automatic
        # Relying on a user to mke them in every module event is error prone
        events.Events.powerupPickup(self, event, _, thread_lock)

        server = self.servers[event['port']]
        if server.map.name !=  self.map: return
        if event['powerup'] != 'Ball': return

        player = server.get_player_by_number(event['player'])

        SpeedyModule.speedy_event.clear()
        SpeedyModule.speedy_thread = Thread(target=self.be_speedy, args=(server, player, SpeedyModule.speedy_event), daemon=True)
        SpeedyModule.speedy_thread.start()


    def powerupUse(self, event, _, thread_lock):
        events.Events.powerupUse(self, event, _, thread_lock)

        server = self.servers[event['port']]
        if server.map.name !=  self.map: return
        if event['powerup'] != 'Ball': return

        SpeedyModule.speedy_event.set()

