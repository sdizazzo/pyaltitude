import time
import logging
from datetime import datetime, timezone, timedelta, tzinfo

from pyaltitude.player import Player
from pyaltitude.game import Game
from pyaltitude.enums import MapState

import pyaltitude.db as database

import ujson

logger = logging.getLogger(__name__)


#this does not belong here
class EST(tzinfo):
    def utcoffset(self, dt):
        return timedelta(hours=-5)
    def tzname(self, dt):
        return "EST"
    def dst(self, dt):
        return timedelta(hours=-5)


class Events(object):

    def sessionStart(self, event):
        #{'date': '2020 Feb 22 04:01:43:847 EST', 'port': -1, 'time': 0, 'type': 'sessionStart'}
        date_str = event['date'][:-8]
        date = datetime.strptime(date_str, "%Y %b %d %H:%M:%S").replace(tzinfo=EST())
        logger.info("Session officially starts at (Nimbly time): %s" % date)
        for server in self.config.server_manager.servers:
            server.start = date
            server.time = 0

    def serverInit(self, event):
        pass


    def clientAdd(self, event):
        server = self.config.get_server(event['port'])
        player = Player(server)
        player = player.parse(event)
        server.add_player(player)

        if player.is_bot(): return

        database.client_add(player, server, event)


    def clientRemove(self, event):
        server = self.config.get_server(event['port'])

        player = server.get_player_by_vaporId(event['vaporId'])
        server.remove_player(player, event['reason'], event['message'])


        #Cleanup the player
        for team in server.game.teams:
            if player in team.players:
                logger.debug('Removing %s from Team #%s, server: %s' % (player.nickname, team.number, server.serverName))
                team.players.remove(player)

        if player.is_bot(): return

        database.client_remove(player, server, event)

    def despawn(self, event):
        """
        {'plane': 'Explodet',
            'stats': {'Crashes': 0, 'Kills': 0, 'Longest Life': 0, 'Ball Possession Time': 0, 'Goals Scored': 0, 'Damage Received': 100.41283, 'Assists': 1, 'Experience': 4, 'Damage Dealt': 0, 'Goals Assisted': 0, 'Damage Dealt to Enemy Buildings': 0, 'Deaths': 1, 'Multikill': 0, 'Kill Streak': 0}, 'port': 27286, 'perkGreen': 'Heavy Armor', 'perkRed': 'Director', 'skin': 'No Skin', 'team': 7, 'time': 52997, 'type': 'despawn', 'perkBlue': 'Reverse Thrust', 'player': 22}
        """
        server = self.config.get_server(event['port'])
        player = server.get_player_by_number(event['player'])

        #player died, update his stats!
        # NOTE: if the server removes a player for timing out
        # need to check they exist before updating them
        # Despawn is probably called before clientRemove
        if player and not player.is_bot():
            database.update_player_stats(player, server, event)
        player.spawn_time = None


    def spawn(self, event):
        server = self.config.get_server(event['port'])
        player = server.get_player_by_number(event['player'])
        player.spawned(event['time'])


    def logPlanePositions(self, event):
        server = self.config.get_server(event['port'])
        server.map_player_positions(event)


    def mapLoading(self, event):
        pass


    def serverHitch(self, event):
        server = self.config.get_server(event['port'])
        server.serverMessage('ServerHitch: %.2f' % event['duration'])
        logger.warning('ServerHitch: %.2f, %s' % (event['duration'], server.serverName))


    def roundEnd(self, event):
        #TODO Clean this UP!!
        server = self.config.get_server(event['port'])
        event['players'] = list()
        for i in event['participants']:
            event['players'].append(server.get_player_by_number(i, bots=True))

        game_stats = dict()
        for player in event['players']:
            p_stats = dict()
            for stat, vals in event['participantStatsByName'].items():
                try:
                    p_stats[stat] = vals[player.player]
                except IndexError:
                    continue
            p_stats['awards'] = list()

            #I know this horrible to do this nested but for now
            for award, i in event['winnerByAward'].items():
                if i == player.player:
                    p_stats['awards'].append(award)
            game_stats[player] = p_stats

        #for p, stats in game_stats.items():
        #    if p.is_bot(): continue
        #    for name, val in stats.items():
        #        logger.info("STATS for %s: %s: %s" % (player.nickname, name, val))

        server.game.stop(game_stats)


    def powerupUse(self, event):
        pass


    def powerupAutoUse(self, event):
        pass


    def powerupPickup(self, event):
        pass


    def mapChange(self, event):
        server = self.config.get_server(event['port'])
        #{"mode":"ball","rightTeam":5,"port":27278,"leftTeam":6,"time":5808529,"type":"mapChange","map":"ball_cave"}

        server.game = Game(server, self.config, event)
        server.game.start()


    def playerInfoEv(self, event):
        server = self.config.get_server(event['port'])
        if event['leaving']: return

        player = server.get_player_by_number(event['player'])
        player.parse_playerInfoEv(event)


    def teamChange(self, event):
        server = self.config.get_server(event['port'])
        player = server.get_player_by_number(event['player'])
        team = server.game.get_team_by_number(event['team'])

        if not player.is_bot():
            logger.info('Adding %s to Team #%s, server: %s' % (player.nickname, team.number, server.serverName) )
        team.add_player(player)

        for t in server.game.teams:
            if t is team: continue
            if player in t.players:
                if not player.is_bot():
                    logger.info('Removing %s from Team #%s, server: %s' % (player.nickname, t.number, server.serverName))
                t.remove_player(player)

        for team in server.game.teams:
            for player in team.get_players():
                logger.debug('Server: %s  Team #%s  Player: %s' % (server.serverName, team.number, player.nickname))

        #DEPRECATED
        player.team = event['team']


    def attach(self, server, from_player, to_player):
        #TODO needs tobe fixed for Team()
        if from_player.team == 2:
            from_player.whisper("Can't attach from spec")
            return
        if to_player.team == 2:
            from_player.whisper("Can't attach to a player in spec")
            return
        if not to_player.is_alive():
            from_player.whisper("Can't attach. %s is dead!" % to_player.nickname)
            return
        if from_player.attached:
            from_player.whisper("You've already attached once this life!")
            return
        if from_player == to_player:
            from_player.whisper('Not a chance!!')
            return
        elif not from_player.team == to_player.team:
            from_player.whisper('You can only attach to members of your own team!')
            return

        from_player.whisper('Attaching to %s' % to_player.nickname)
        to_player.whisper('%s is attaching to you!' % from_player.nickname)

        server.overrideSpawnPoint(from_player, to_player.x, to_player.y, 0)
        server.assignTeam(from_player, 0 if from_player.team == server.map.leftTeam else 1)
        from_player.attached = True
        logger.info('%s attached to %s' % (from_player.nickname, to_player.nickname))


    def consoleCommandExecute(self, event):
        server = self.config.get_server(event['port'])

        #
        # Custom commands - More shit to do!!!
        #
        # TODO Needs to be broken out into its own piece
        #
        from_player = None
        to_player = None
        if event['command'] in ( 'a', 'attach'):
            #print('THE EVENT', event)
            from_player = server.get_player_by_vaporId(event['source'])
            if event['command'] == 'a':
                to_player = from_player.last_attached_player
                if not to_player:
                    from_player.whisper("You haven't attached to anybody yet")
                    return
            else:
                to_player = server.get_player_by_name(event['arguments'][0])
                from_player.last_attached_player = to_player

            self.attach(server, from_player, to_player)


        #command needs to be called dynamilcally instead
        #Similarlly to modules
        #THis is adding too much complexity for this week
        ##TODO for when I am
        #    command = Attach(server, from_player, to_player)
        #    command.execute()

