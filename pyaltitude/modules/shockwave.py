
import asyncio
from . import module
import random


class ShockWaveModule(module.GameModeModule):
    #
    # Not really set to work on just TBD yet!!
    #
    def __init__(self, mode='TBD'):
        self.mode = mode
        super().__init__(self, mode)


    async def kill(self, event, _, servers):
        #{"victimPositionY":407.63,"victimVelocityX":1.17,"streak":3,"source":"plane","type":"kill","victimPositionX":1395.17,"victimVelocityY":2.63,"multi":3,"port":27278,"xp":10,"victim":0,"time":12800875,"player":11}
        async def jiggle(multi, team):
            if not team: return

            for player in team:
                if not player.is_bot():
                    await player.whisper('MULTI-KILL (%s) OMEGA BURST INCOMING!!!' %  multi)
                    #await player.whisper('TAKE COVER!!!')
                for i in range(1, multi+2):
                    await player.applyForce(random.randrange(i*-5,i*5),random.randrange(i*-5,i*5))
                    await asyncio.sleep(.2)
                #await player.applyForce(random.randrange(-10,10),random.randrange(-10,10))
                #await asyncio.sleep(.1)
                #await player.applyForce(random.randrange(-8,8),random.randrange(-8,8))

        server = servers[event['port']]
        player = await server.get_player_by_number(event['player'])
        teams = server.get_players_by_team()
        if event['multi'] > 1:
            if player in teams['leftTeam']:
                await jiggle(event['multi'],teams.get('rightTeam'))
            else:
                await jiggle(event['multi'], teams.get('leftTeam'))

    async def structureDamage(self, event, _, servers):
        async def jiggle(team):
            if not team: return

            for player in team:
                if not player.is_bot():
                    await player.whisper('BEWARE SHOCK WAVE FROM BASE DAMAGE!')
                await player.applyForce(random.randrange(-12,12),random.randrange(-12,12))
                await asyncio.sleep(.2)
                await player.applyForce(random.randrange(-10,10),random.randrange(-10,10))
                await asyncio.sleep(.2)
                await player.applyForce(random.randrange(-8,8),random.randrange(-8,8))

        server = servers[event['port']]
        # for testing
        #{"positionY":475,"port":27278,"exactXp":31.25,"xp":31,"time":5135540,"type":"structureDamage","player":3,"target":"base","positionX":3184}  
        player = await server.get_player_by_number(event['player'])
        teams = server.get_players_by_team()
        if event['target'] == 'base':
            if player in teams['leftTeam']:
                await jiggle(teams.get('rightTeam'))
            else:
                await jiggle(teams.get('leftTeam'))

    async def structureDestroy(self, event, _, servers):
        async def jiggle(team):
            for player in team:
                if not player.is_bot():
                    await player.whisper('SHRAPNAL INCOMING FROM DESTROYED TURRET!')
                await player.applyForce(random.randrange(-10,10),random.randrange(-10,10))
                await asyncio.sleep(.1)
                await player.applyForce(random.randrange(-8,8),random.randrange(-8,8))

        server = servers[event['port']]
        player = await server.get_player_by_number(event['player'])
        teams = server.get_players_by_team()
        if event['target'] == 'turret':
            if player in teams.get('leftTeam'):
                await jiggle(teams.get('rightTeam'))
            else:
                await jiggle(teams.get('leftTeam'))
