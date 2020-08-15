
import logging

from datetime import datetime
from collections import namedtuple
import pprint

from .map import Map
from .enums import GameMode
import pyaltitude.db as database

logger = logging.getLogger(__name__)

pp = pprint.PrettyPrinter(indent=4)


class PlayerTimer(object):
    def __init__(self, enter):
        self.enter = enter
        self.duration = 0


class Team(object): #TODO breakout HasPlayers()
    def __init__(self, server, config, number):
        self.server = server
        self.config = config
        self.number = number
        self.players = list()

        self.score = 0
        # if player drops they don't get credit if team wins, since time played
        # will be under the 85% threshold, but they will be charged the loss
        # and marked with a dropped_game against their record

        # can join in middle or not?
        # only if 2 ppl at same time
        # one person tries and is marked wants_in
        # if 2 ppl that fit criteria in spec want in,
        # then add them at same time
        self.player2timer = dict()


    def add_player(self, player):
        """
            Each player has a DateTime associated with when
            they joined or left the team.
        """
        #UGLY!
        if player.is_bot():
            #dont track bots
            pass
        elif player not in self.player2timer:
            self.player2timer[player] = PlayerTimer(datetime.now())
        else:
            #If we've already played on this team, use the
            #same instance and overwrite the .enter attr
            # would be better to use a namedTuple and not modify the instance
            self.player2timer[player].enter = datetime.now()

        self.players.append(player)


    def remove_player(self, player):
        for p in self.players:
            if player == p:
                if not player.is_bot():
                    #also mark the duration for the player in player2timer
                    session_dur = (datetime.now() - self.player2timer[player].enter).seconds
                    self.player2timer[player].duration += session_dur
                self.players.remove(p)


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


    def stop(self, game_stats):
        """
            Pretty sure we write every game to the DB whether its competitive or
            not, because we want to track kills/deaths.

            We can decide to display competitve games based on the number of
            players or something later.

            Save game state and write everything to the db when the game is
            over if we had players join and play a competetive game.

        """
        self.ended = datetime.now()
        game_dur = (self.ended-self.started).seconds # WARMUP
        logger.info("Game ended: server: %s,  mode: %s,  duration: %s" % (self.server.serverName, self.mode, (self.ended-self.started).seconds))

        #add current players to the player2timer
        for team in self.teams:
            #logger.warning('TEAM #%s' % team.number)
            for player in team.players:
                team.remove_player(player)


        for player, stat in game_stats.items():
            #write kill/death/crash/goals/dmg recieve/dmg dealt/awards to DB

            if player.is_bot(): continue
            player.whisper('your game stats')
            player.whisper('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            for k, v in stat.items():
                if k == 'awards': continue
                if not v: continue
                player.whisper('%s: %s' % (k, v))


        #logger.warning(pp.pformat(game_stats))
        #if self.mode in (GameMode.TBD, GameMode.BALL) and \
        #                (team.get_players() for team in self.teams):
        #    self.write_to_db(event)


    def write_to_db(self, game_stats):
        # Rules
        # 1x1 2x2 3x3 4x4 ... 8x8
        # must play 90% of game for win
        # if you play at all on a team (1%) and dont finish, you get a drop and
        #    a loss if you lose, not a win

        """
        {"port":27278,
         "participantStatsByName":{"Crashes":[2,0,2,3,1,2,3],"Kills":[2,1,5,3,4,1,5],"Longest Life":[67,26,72,61,66,66,38],"Ball Possession Time":[0,0,0,0,0,0,0],"Goals Scored":[0,0,0,0,0,0,0],"Damage Received":[740,0,620,880,770,690,810],"Assists":[4,0,1,5,3,4,0],"Experience":[105,35,201,191,179,86,197],"Damage Dealt":[420,30,360,350,380,410,290],"Goals Assisted":[0,0,0,0,0,0,0],"Damage Dealt to Enemy Buildings":[0,0,1040,1570,0,0,1000],"Deaths":[5,0,5,6,5,6,7],"Multikill":[0,0,0,2,2,0,3],"Kill Streak":[1,1,2,2,2,1,4]},
         "winnerByAward":{"Most Helpful":3,"Best Kill Streak":6,"Longest Life":2,"Most Deadly":2,"Best Multikill":6},
         "time":5200363,
         "type":"roundEnd",
         "participants":[0,1,2,3,4,5,6]}
        """

        #HOW DO WE KNOW WHO WON?

        # we need to filter this list out for bots!
        #Create the game in the DB
        if 1:
            for player, timer in team.player2timer.items():
                percent = (timer.duration/float(game_dur))*100
                logger.info("Player: %s  Team: %s  %.2f%% of game spent" % (player.nickname, team.number, percent))
                if percent > 90:
                    #counts as a win!
                    pass

