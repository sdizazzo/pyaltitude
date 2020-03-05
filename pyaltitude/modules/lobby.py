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


    def portal_runner(self, server, player):
        logger.info('Portal thread started')
        WAIT = .1
        sent = False
        ts = None
        while True:
            if player.game_event.is_set():
                break

            # check their position and see if they are in one of the portals
            if 288 < player.x < 352 and 860 < player.y < 1020:
                if not sent:
                    #need to retry this in case of packet loss
                    #while player in server.get_players():
                    logger.info("Sending changeServer request")
                    server.serverMessage('%s is entering %s' % (player.nickname, server.serverName))
                    server.serverRequestPlayerChangeServer(player.nickname, server.launcher.ip, 27283, secret_code='foo')
                    ts = time.time()
                    sent = True

            if sent and time.time() - ts > 2:
                sent = False

            time.sleep(WAIT)

        logger.info('Portal thread ended.')
        player.game_event.clear()


    #################
    # Events
    #################


    def clientAdd(self, event, _, thread_lock):
        events.Events.clientAdd(self, event, _, thread_lock)
        server = self.servers[event['port']]
        if server.port != self.port: return

        player = server.get_player_by_number(event['player'])

        player.game_thread = Thread(target=self.portal_runner, args=(server, player) , daemon=True)
        player.game_thread.start()


    def clientRemove(self, event, _, thread_lock):
        server = self.servers[event['port']]
        if server.port == self.port:
            player = server.get_player_by_number(event['player'])
            player.game_event.set()
            player.game_thread = None

        #HAVE TO STOP THE EVENT BEFORE WE REMOVE THE PLAYER!!
        events.Events.clientRemove(self, event, _, thread_lock)

