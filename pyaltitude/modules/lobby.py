import time
import logging
from threading import Thread, Event, Lock

from . import module
from .. import map
from .. import events


logger = logging.getLogger(__name__)


"""

Status: In development

The idea behind this module is to make one server that shows up in the server
list that is the main lobby with portals that link to other hidden servers on
the same mavhine.  SO a player would enter the main lobby and then from there
choose which type of game they wanted to play, and enter the portal for that
game, and be moved to that hidden server with all the modules and attributes
and players running.

One issue is that if the servers are hidden, there would be no way to see how
many players are in each one, and thats the main way other players join
servers.  They look at how mnay people are playing and then join them.


"""

# TODO
# How to hide server from main Nimbly list?
# Answer: make it a lan server

# Is there a way for Nimbly to show total number of
# connected players in all of our lan servers on our lobby?

# Make it work!

class Lobby(module.ServerModule):

    def __init__(self, port=27284):
        self.port = port

        super().__init__(self, port)


    def point_in_circle(self, center_x, center_y, x, y, radius=80):
        dx = abs(x-center_x)
        dy = abs(y-center_y)
        R = radius

        if dx>R or dy>R: return False

        if dx + dy <= R:
            return True

        if dx**2 + dy**2 <= R**2:
            return True
        else:
            return False


    def portal_runner(self, server, player):
        logger.info('Portal thread started')
        WAIT = .1
        sent = False
        dest_port = None
        ts = 0
        while True:
            if player.game_event.is_set():
                break

            #Speed ball
            if self.point_in_circle(448, 830, player.x, player.y):
                dest_port = 27283
                #
                # TODO make it nice and tidy
                #
                #player.change_server(servers[port])

            #King of the Hill
            elif self.point_in_circle(2980, 830, player.x, player.y):
                dest_port = 27282

            #FFA Wide Angle
            elif self.point_in_circle(1174, 1264, player.x, player.y):
                dest_port = 27279

            #Wide Angle
            elif self.point_in_circle(2290, 1264, player.x, player.y):
                dest_port = 27278


            if dest_port and not sent:
                dest_server = self.config.server_launcher.server_for_port(dest_port)
                logger.info("Sending %s to server %s" % (player.nickname, dest_server.serverName))
                server.serverMessage('%s is entering %s' % (player.nickname, dest_server.serverName))
                server.serverRequestPlayerChangeServer(player, self.config.server_launcher.ip, dest_port, secret_code=None)
                ts = time.time()
                sent = True

            #need to retry this in case of packet loss
            # TODO It doesn't seem to help, though...
            if sent and time.time() - ts > 2:
                sent = False

            time.sleep(WAIT)

        logger.info('Portal thread ended.')
        player.game_event.clear()


    #################
    # Events
    #################


    def clientAdd(self, event):
        events.Events.clientAdd(self, event)
        server = self.config.server_launcher.server_for_port(event['port'])
        if server.port != self.port: return

        player = server.get_player_by_number(event['player'])

        player.game_thread = Thread(target=self.portal_runner, args=(server, player) , daemon=True)
        player.game_thread.start()


    def clientRemove(self, event):
        server = self.config.server_launcher.server_for_port(event['port'])
        if server.port == self.port:
            player = server.get_player_by_number(event['player'])
            player.game_event.set()
            player.game_thread = None

        #HAVE TO STOP THE EVENT BEFORE WE REMOVE THE PLAYER!!
        events.Events.clientRemove(self, event)

