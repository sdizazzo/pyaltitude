import time
import logging
from threading import Thread, Event, Lock

from . import module
from .. import map
from .. import events


logger = logging.getLogger(__name__)


class KOTH(module.MapModule):

    flag_timer_thread =None
    flag_timer_event = Event()
    flag_taken_by = None
    flag_taken_at = 0
    leftscore = 0
    rightscore = 0
    lefttime = 0
    righttime = 0

    def __init__(self, map='ball_king_pyramid'):
        self.map_name = map
        
        # CANT USE INSTANCE VARIABLES!!!!!
        # BECAUSE EACH WORKER WOULD GET A DIFFERNT
        # COPY!!!!!!!!!!! 
        # USE CLASS VARIABLES ABOVE INSTEAD!!!!

        # Also dont forget that whenever updating a
        # class variable, you must do it within the
        # context of the thread lock ie.

        # with thread_lock:
        #     KOTH.flag_taken_by = player

        #...BUT...  I believe that's only possible/necessary
        # in the events, which are executed in the worker threads
        # if modified in the main class, you shouldn't need
        # to use the thread_lock

        super().__init__(self, map)

    #if noplayers are left on a team, the flag should go back to neutral, 
    # ie, the flag_timer_should stop


    def reset(self, server):
        logger.info('Resetting KOTH game')
        KOTH.flag_timer_thread = None
        KOTH.flag_timer_event = Event()
        KOTH.flag_taken_by = None
        KOTH.flag_taken_at = 0
        KOTH.leftscore = 0
        KOTH.rightscore = 0
        KOTH.lefttime = 0
        KOTH.righttime = 0
        server.overrideBallScore(0, 0)


    def flag_timer(self, server, player, event):
        logger.debug('Flag timer started')
        t = 0
        WAIT = 1
        while True:
            if event.is_set():
                #It doesn't exist yet
                #player.flag_hold_time += t
                
                #Also need to set the KOTH.lefttime and righttime
                #so we can score off of partial holds, instead of
                # waiting for complete minutes
                break

            team_color = 'blue' if player.team == server.map.leftTeam else 'orange'
            other_team = 'blue' if team_color is 'orange' else 'orange'

            if t and t%60 == 0:
                t = 0
                server.serverMessage("... DING! ...")
                server.serverMessage("... DING! ...")
                server.serverMessage("... DING! ...")
                server.serverMessage('Score one for the %ss!!!' % team_color)

                left = 1 if player.team == server.map.leftTeam else 0
                right = 1 if player.team == server.map.rightTeam else 0
                
                KOTH.leftscore += left
                KOTH.rightscore += right
                server.overrideBallScore(KOTH.leftscore, KOTH.rightscore)
 
                logger.info('The %s team scored.  Score: %s %s' % (team_color, KOTH.leftscore, KOTH.rightscore))

            elif t == 30:
                server.serverMessage('30 seconds remaining...  Get to work %s.' % other_team)
            elif t == 40:
                server.serverMessage('20 seconds remaining...  Entering danger zone!')
            elif t == 50:
                server.serverMessage("...................................10")
            elif t == 51:
                server.serverMessage("................................9")
            elif t == 52:
                server.serverMessage("............................8")
            elif t == 53:
                server.serverMessage("........................7")
            elif t == 54:
                server.serverMessage("....................6")
            elif t == 55:
                server.serverMessage("................5")
            elif t == 56:
                server.serverMessage("............4")
            elif t == 57:
                server.serverMessage("........3")
            elif t == 58:
                server.serverMessage("....2")
            elif t == 59:
                server.serverMessage("1")
 

            time.sleep(WAIT)
            t +=1

        logger.debug('Flag timer ended')


    #################
    # Events
    #################


    def serverInit(self, event):
        events.Events.serverInit(self, event)
        server = self.config.get_server(event['port'])
        logger.info('Setting cameraViewScale to 120')
        server.testCameraViewScale(120)
        logger.info('Setting gravityMode to 3')
        server.testGravityMode(3)


    def clientAdd(self, event):
        events.Events.clientAdd(self, event)
        server = self.config.get_server(event['port'])
        #if server.port != 27282: return

        player = server.get_player_by_number(event['player'])
        if not player.is_bot():
            logger.info("%s joined %s from %s" % (player.nickname, server.serverName, player.ip))
            player.whisper("*********************************************************************")
            player.whisper("Enter the base and touch the flag inside to claim it for")
            player.whisper("your team.  Then keep the other team from touching it!")
            player.whisper("Hold it for one minute consecutively to score a point.")
            player.whisper("~~~Special Commands~~~")
            player.whisper("/attach <player_name> - Spawn at your teammate's loc")
            player.whisper("/a - Shortcut to attach to your last attached teammate.")
            player.whisper("*********************************************************************")


    def mapChange(self, event):
        # NOTE
        # When  you override an event in a module, you
        # need to call the basic mapChange first!!
        # then extend it with our stuff
        #
        #
        # TODO This will get us closer to breaking
        # out the modules into types: server, game, map
        events.Events.mapChange(self, event)

        server = self.config.get_server(event['port'])
        if server.port == 27282:
            with self.thread_lock:
                KOTH.flag_timer_event.set()
                time.sleep(2)
                self.reset(server)


    def powerupAutoUse(self, event):
        events.Events.powerupAutoUse(self, event)

        server = self.config.get_server(event['port'])
        if server.map.name != self.map_name: return
        if event['powerup'] != 'Health' or (event['positionX'], event['positionY']) != (1501, 1735): return
        #THis is the right powerup
        player = server.get_player_by_number(event['player'])
        #if not player: return
        
        with self.thread_lock:
            if not KOTH.flag_taken_by or KOTH.flag_taken_by.team != player.team:
                #its an event we need to pay attention to
                if KOTH.flag_timer_thread:
                    #flag was taken back by the other team
                    #print out how long it was held for and store it
                    #server.serverMessage()
                    
                    #stop the last timer
                    self.flag_timer_event.set()

                team_color = 'blue' if player.team == server.map.leftTeam else 'orange'
                other_color = 'orange' if team_color == 'blue' else 'blue'
                server.serverMessage("%s grabbed the flag for the %s team!!" % (player.nickname, team_color))
                logger.info('%s took the flag for the %s team' % (player.nickname, team_color))

                KOTH.flag_taken_by = player
                KOTH.flag_taken_at = event['time']
                KOTH.flag_timer_event = Event()
                #start a new timer for this player
                KOTH.flag_timer_thread = Thread(target=self.flag_timer, args=(server, player, KOTH.flag_timer_event), daemon=True)
                KOTH.flag_timer_thread.start() 

