import time
from threading import Thread, Event
from . import module
from .. import map


class Turf(module.MapModule):
    flag_timer_thread =None
    flag_timer_event = Event()
    flag_taken_by = None
    flag_taken_at = 0
    leftscore = 0
    rightscore = 0
    lefttime = 0
    righttime = 0

    def __init__(self, map='ball_pyramid_turf'):
        self.map_name = map
        
        # CANT USE INSTANCE VARIABLES!!!!!
        # BECAUSE EACH WORKER WOULD GET A DIFFERNT
        # COPY!!!!!!!!!!! 
        
        #USE CLASS VARIABLES ABOVE INSTEAD!!!!

        super().__init__(self, map)

    #if noplayers are left on a team, the flag should go back to neutral, 
    # ie, the flag_timer_should stop


    def reset(self, server):
        Turf.flag_timer_thread =None
        Turf.flag_timer_event = Event()
        Turf.flag_taken_by = None
        Turf.flag_taken_at = 0
        Turf.leftscore = 0
        Turf.rightscore = 0
        Turf.lefttime = 0
        Turf.righttime = 0
        server.overrideBallScore(0, 0)


    def flag_timer(self, server, player, event):
        t = 0
        WAIT = 1
        while True:
            if event.is_set():
                #It doesn't exist yet
                #player.flag_hold_time += t
                
                #Also need to set the Turf.lefttime and righttime
                #so we can score off of partial holds, instead of
                # waiting for complete minutes
                break

            if t and t%60 == 0:
                team_color = 'Blue' if player.team == server.map.leftTeam else 'Orange'
                server.serverMessage('%s Team is holding the base!!!  Point scored!!' % team_color)

                left = 1 if player.team == server.map.leftTeam else 0
                right = 1 if player.team == server.map.rightTeam else 0
                
                Turf.leftscore += left
                Turf.rightscore += right
                server.overrideBallScore(Turf.leftscore, Turf.rightscore)

            time.sleep(WAIT)
            t +=1

        print('Thread ending...')


    def roundEnd(self, event, _):
        server = self.servers[event['port']]
        if server.map.name != self.map_name: return
        time.sleep(18)
        self.reset(server)


    def powerupAutoUse(self, event, _):
        server = self.servers[event['port']]
        # {"powerup":"Health","positionY":1641,"playerVelX":2.43,"playerVelY":-0.3,"port":27282,"velocityX":0,"time":169837,"type":"powerupAutoUse","velocityY":0,"player":0,"positionX":1502}
        if server.map.name != self.map_name: return
        if event['powerup'] != 'Health' or (event['positionX'], event['positionY']) != (1502, 1641): return

        
        player = server.get_player_by_number(event['player'])
        if not player: return

        if not Turf.flag_taken_by or Turf.flag_taken_by.team != player.team:
            if Turf.flag_timer_thread:
                #flag was taken by the other team
                #print out how long it was held for and store it
                #server.serverMessage()
                self.flag_timer_event.set()

            team_color = 'blue' if player.team == server.map.leftTeam else 'orange'

            server.serverMessage("%s grabbed the flag for the %s team!!" % (player.nickname, team_color))

            Turf.flag_taken_by = player
            Turf.flag_taken_at = event['time']
            Turf.flag_timer_event = Event()
            Turf.flag_timer_thread = Thread(target=self.flag_timer, args=(server, player, Turf.flag_timer_event), daemon=True)
            Turf.flag_timer_thread.start() 

