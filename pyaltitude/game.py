
import logging

from datetime import datetime
from collections import namedtuple

from .map import Map
from .enums import GameMode


logger = logging.getLogger(__name__)

#MockMap = namedtuple('MockMap', ('state', 'name'), defaults = (None, None))


class Team(object): #TODO breakout HasPlayers()
    def __init__(self, server, config, number):
        self.server = server
        self.config = config
        self.number = number
        self.players = list()
        self.score = 0


    def whisper(self, message):
        for player in self.get_players():
            player.whisper(message)


    def get_players(self, bots=False):
        pl = list()
        for p in self.players:
            if not bots and p.is_bot():
                continue
            pl.append(p)
        return pl


    def get_player_by_number(self, number, bots=True):
        for p in self.get_players(bots=bots):
            if p.player == number:
                return p 


class Game(object):
    mode2enum = {
                 'ffa':GameMode.FFA, 'tbd':GameMode.TBD,
                 'tdm':GameMode.TDM, '1bd':GameMode.ONEBD,
                 '1de':GameMode.ONEDE, '1dm':GameMode.ONEDM,
                 'ball': GameMode.BALL
                }


    def __init__(self, server, config, event):
        #{"mode":"ball","rightTeam":5,"port":27278,"leftTeam":6,"time":5808529,"type":"mapChange","map":"ball_cave"}
        self.server = server
        self.config = config
        self.started = None
        self.ended = None

        self.mode = Game.mode2enum[event['mode']]
        self.map = Map(server, config,
                       event['rightTeam'],
                       event['leftTeam'],
                       event['map'])

        self.teams = list()

    
    def get_team_by_number(self, number):
        """
            If a team is requested that doesn't exist, create it.
        """
        for team in self.teams:
            if team.number == int(number):
                return team

        team = Team(self.server, self.config, number)
        self.teams.append(team)
        return team


    def start(self):
        self.started = datetime.now()
        logger.info("Game started: server: %s,  mode: %s,  map: %s" % (self.server.serverName, self.mode, self.map.name))


    def stop(self):
        self.ended = datetime.now()
        logger.info("Game ended: server: %s,  mode: %s,  duration: %s" % (self.server.serverName, self.mode, (self.ended-self.started).seconds))


