import time
from . import module

class BallFlipGravityModule(module.MapModule):
    def __init__(self, map='ball_space_balls'):
        self.map = map
        super().__init__(self, map)

    def powerupPickup(self, event):
        server = self.config.server_launcher.server_for_port(event['port'])
        #
        # HACK!!!!!!!!!!!!!!!!!!!!!!!!
        #
        #this is not working as a MapModule yet, so I'm just going to check
        # here for now
        if server.map.name !=  self.map: return
        if event['powerup'] != 'Ball': return

        player = server.get_player_by_number(event['player'])
        server.testGravityMode(2)
        #server.serverMessage('Ball is held...Gravity has been disrupted!')


    def powerupUse(self, event):
        server = self.config.server_launcher.server_for_port(event['port'])
        if server.map.name !=  self.map: return
        if event['powerup'] != 'Ball': return

        player = server.get_player_by_number(event['player'])
        server.testGravityMode(0)
        #server.serverMessage('Gravity has returned to normal.')

