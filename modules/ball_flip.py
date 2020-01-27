import asyncio
from . import module

class BallFlipGravityModule(module.MapModule):
    def __init__(self, map='ball_space_balls'):
        self.map = map
        super().__init__(self, map)

    async def powerupPickup(self, event, _, servers):
        server = servers[event['port']]
        #
        # HACK!!!!!!!!!!!!!!!!!!!!!!!!
        #
        #this is not working as a MapModule yet, so I'm just going to check
        # here for now
        if server.active_map.name !=  self.map: return
        if event['powerup'] != 'Ball': return

        player = await server.get_player_by_number(event['player'])
        await server.testGravityMode(2)
        #await server.serverMessage('Ball is held...Gravity has been disrupted!')


    async def powerupUse(self, event, _, servers):
        server = servers[event['port']]
        if server.active_map.name !=  self.map: return
        if event['powerup'] != 'Ball': return

        player = await server.get_player_by_number(event['player'])
        await server.testGravityMode(0)
        #await server.serverMessage('Gravity has returned to normal.')

