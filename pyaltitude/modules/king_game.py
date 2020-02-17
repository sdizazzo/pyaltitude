import time
from threading import Thread, Event, Lock

from . import module
from .. import map
from .. import events

class KingGame(module.MapModule):
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
        
        # Also dont forget that whenever updating a
        # class variable, you must do it within the
        # context of the thread lock ie.

        # with thread_lock:
        #     KingGame.flag_taken_by = player

        #...BUT...  I believe that's only possible/necessary
        # in the events, which are executed in the worker threads
        # if modified in the main class, you shouldn't need
        # to use the thread_lock

        #USE CLASS VARIABLES ABOVE INSTEAD!!!!

        super().__init__(self, map)

    #if noplayers are left on a team, the flag should go back to neutral, 
    # ie, the flag_timer_should stop


    def reset(self, server):
        KingGame.flag_timer_thread = None
        KingGame.flag_timer_event = Event()
        KingGame.flag_taken_by = None
        KingGame.flag_taken_at = 0
        KingGame.leftscore = 0
        KingGame.rightscore = 0
        KingGame.lefttime = 0
        KingGame.righttime = 0
        server.overrideBallScore(0, 0)


    def flag_timer(self, server, player, event):
        t = 0
        WAIT = 1
        while True:
            if event.is_set():
                #It doesn't exist yet
                #player.flag_hold_time += t
                
                #Also need to set the KingGame.lefttime and righttime
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
                
                KingGame.leftscore += left
                KingGame.rightscore += right
                server.overrideBallScore(KingGame.leftscore, KingGame.rightscore)
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

        print('Thread ending...')


    #################
    # Events
    #################

    def roundEnd(self, event, _, thread_lock):
        events.Events.roundEnd(self, event, _, thread_lock)

        server = self.servers[event['port']]
        if server.map.name != self.map_name: return
        
        with thread_lock:
            KingGame.flag_timer_event.set()
            time.sleep(2)
            pass # <--- ???
            time.sleep(18)
            self.reset(server)


    def mapChange(self, event, _, thread_lock):
        # NOTE
        # When  you override an event in a module, you
        # need to call the basic mapChange first!!
        # then extend it with our stuff
        #
        #
        # TODO This will get us closer to breaking
        # out the modules into types: server, game, map
        events.Events.mapChange(self, event, _, thread_lock)

        server = self.servers[event['port']]
        if server.port == 27282:
            with thread_lock:
                KingGame.flag_timer_event.set()
                time.sleep(2)
                self.reset(server)


    def powerupAutoUse(self, event, _, thread_lock):
        events.Events.powerupAutoUse(self, event, _, thread_lock)

        server = self.servers[event['port']]
        if server.map.name != self.map_name: return
        if event['powerup'] != 'Health' or (event['positionX'], event['positionY']) != (1501, 1735): return

        
        player = server.get_player_by_number(event['player'])
        if not player: return

        
        with thread_lock:
            if not KingGame.flag_taken_by or KingGame.flag_taken_by.team != player.team:
                if KingGame.flag_timer_thread:
                    #flag was taken back by the other team
                    #print out how long it was held for and store it
                    #server.serverMessage()
                    self.flag_timer_event.set()

                team_color = 'blue' if player.team == server.map.leftTeam else 'orange'
                other_color = 'orange' if team_color == 'blue' else 'blue'
                server.serverMessage("%s grabbed the flag for the %s team!!" % (player.nickname, team_color))
                
                KingGame.flag_taken_by = player
                KingGame.flag_taken_at = event['time']
                KingGame.flag_timer_event = Event()
                KingGame.flag_timer_thread = Thread(target=self.flag_timer, args=(server, player, KingGame.flag_timer_event), daemon=True)
                KingGame.flag_timer_thread.start() 

