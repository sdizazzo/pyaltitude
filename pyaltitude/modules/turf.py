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
    
    def __init__(self, map='ball_turf_testing'):
        self.map_name = map
        
        # CANT USE INSTANCE VARIABLES!!!!!
        # BECAUSE EACH WORKER WOULD GET A DIFFERNT
        # COPY!!!!!!!!!!! 
        
        #USE CLASS VARIABLES ABOVE INSTEAD!!!!

        super().__init__(self, map)

    def reset(self, server):
        Turf.flag_timer_thread =None
        Turf.flag_timer_event = Event()
        Turf.flag_taken_by = None
        Turf.flag_taken_at = 0
        Turf.leftscore = 0
        Turf.rightscore = 0
        server.overrideBallScore(0, 0)

    def flag_timer(self, server, player, event):
        t = 0
        while True:
            if event.is_set():
                print("Event is set")
                t = 0
                break

            if t and t%60 == 0:
                server.serverMessage('Team %s is holding!!!  Scored a point!!' % player.team)
                
                #TODO what if a player goes to spec after capturing the flag?
                left = 1 if player.team == server.map.leftTeam else 0
                right = 1 if player.team == server.map.rightTeam else 0
                
                server.overrideBallScore(Turf.leftscore+left, Turf.rightscore+right)
                Turf.leftscore = Turf.leftscore+left
                Turf.rightscore = Turf.rightscore+right

            time.sleep(1)
            t +=1

        print('Thread ending...')


    def roundEnd(self, event, _):
        server = self.servers[event['port']]
        if server.map.name != self.map_name: return
        print('IN ROUNDEND!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!') 
        print(Turf.flag_timer_thread)
        Turf.flag_timer_event.set()
        time.sleep(2)
        print(Turf.flag_timer_thread)
        time.sleep(15)
        self.reset(server)


    def powerupAutoUse(self, event, _):
        #{"powerup":"Health","positionY":749,"playerVelX":-4.52,"playerVelY":3.41,"port":27282,"velocityX":0,"time":48699,"type":"powerupAutoUse","velocityY":0,"player":0,"positionX":656}
        server = self.servers[event['port']]
        #
        # HACK!!!!!!!!!!!!!!!!!!!!!!!!
        #
        #this is not working as a MapModule yet, so I'm just going to check
        # here for now
        if server.map.name != self.map_name: return
        if event['powerup'] != 'Health' or (event['positionX'], event['positionY']) != (656, 749): return

        
        player = server.get_player_by_number(event['player'])
        if not player: return

        if not Turf.flag_taken_by or Turf.flag_taken_by.team != player.team:
            print(Turf.flag_taken_by)
            if Turf.flag_timer_thread:
                print("Stopping thread since somebody else grabbed it")
                self.flag_timer_event.set()
                #let the thread die and then reset state
                time.sleep(1)
                Turf.flag_timer_event.clear()

            server.serverMessage("%s picked up the flag for team %s!!" % (player.nickname, player.team))
            Turf.flag_taken_by = player
            Turf.flag_taken_at = event['time']
            Turf.flag_timer_thread = Thread(target=self.flag_timer, args=(server, player, Turf.flag_timer_event), daemon=True)
            Turf.flag_timer_thread.start() 

