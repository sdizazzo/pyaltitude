
import time
from . import module
import random


class ShockWaveModule(module.GameModeModule):
    #
    # Not really set to work on just TBD yet!!
    #
    def __init__(self, mode='TBD'):
        self.mode = mode
        super().__init__(self, mode)


    def kill(self, event, _):
        #{"victimPositionY":407.63,"victimVelocityX":1.17,"streak":3,"source":"plane","type":"kill","victimPositionX":1395.17,"victimVelocityY":2.63,"multi":3,"port":27278,"xp":10,"victim":0,"time":12800875,"player":11}
        def jiggle(multi, team):
            if not team: return

            for player in team:
                if not player.is_bot():
                    player.whisper('MULTI-KILL (%s) OMEGA BURST INCOMING!!!' %  multi)
                for i in range(1, multi+2):
                    player.applyForce(random.randrange(i*-5,i*5),random.randrange(i*-5,i*5))
                    time.sleep(.2)
                #player.applyForce(random.randrange(-10,10),random.randrange(-10,10))
                #time.sleep(.1)
                #player.applyForce(random.randrange(-8,8),random.randrange(-8,8))

        server = self.servers[event['port']]
        if not server.map.state.ACTIVE: return

        player = server.get_player_by_number(event['player'])
        if not player: return

        teams = server.get_players_by_team()
        if event['multi'] > 1:
            if player in teams['leftTeam']:
                jiggle(event['multi'],teams.get('rightTeam'))
            else:
                jiggle(event['multi'], teams.get('leftTeam'))

    def structureDamage(self, event, _):
        def jiggle(team):
            if not team: return

            for player in team:
                if not player.is_bot():
                    player.whisper('BEWARE SHOCK WAVE FROM BASE DAMAGE!')
                player.applyForce(random.randrange(-12,12),random.randrange(-12,12))
                time.sleep(.2)
                player.applyForce(random.randrange(-10,10),random.randrange(-10,10))
                time.sleep(.2)
                player.applyForce(random.randrange(-8,8),random.randrange(-8,8))

        server = self.servers[event['port']]
        if not server.map.state.ACTIVE: return
        # for testing
        #{"positionY":475,"port":27278,"exactXp":31.25,"xp":31,"time":5135540,"type":"structureDamage","player":3,"target":"base","positionX":3184}  
        player = server.get_player_by_number(event['player'])
        if not player: return

        teams = server.get_players_by_team()
        if event['target'] == 'base':
            if player in teams['leftTeam']:
                jiggle(teams.get('rightTeam'))
            else:
                jiggle(teams.get('leftTeam'))

    def structureDestroy(self, event, _):
        def jiggle(team):
            for player in team:
                if not player.is_bot():
                    player.whisper('SHRAPNAL INCOMING FROM DESTROYED TURRET!')
                player.applyForce(random.randrange(-10,10),random.randrange(-10,10))
                time.sleep(.2)
                player.applyForce(random.randrange(-8,8),random.randrange(-8,8))

        
        server = self.servers[event['port']]
        if not server.map.state.ACTIVE: return
        
        player = server.get_player_by_number(event['player'])
        if not player: return

        teams = server.get_players_by_team()
        if event['target'] == 'turret':
            if player in teams.get('leftTeam'):
                jiggle(teams.get('rightTeam'))
            else:
                jiggle(teams.get('leftTeam'))
