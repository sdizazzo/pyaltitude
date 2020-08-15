from .model import *
from .enums import GameMode



def transaction(func):
    def wrapper(player, server, event):
        try:
            func(player, server, event)
        except:
            server.session.rollback()
            raise
    return wrapper


@transaction
def client_add(player, server, event):
    dbserver = get_or_create(server.session, DBServer, port=server.port, name=server.serverName)
    dbnickname = get_or_create(server.session, DBNickname, nickname=player.nickname)
    dbhost = get_or_create(server.session, DBHost, address=player.ip.split(':')[0])
    dbplayer = get_or_create(server.session, DBPlayer, vapor_id=player.vaporId)

    if not dbnickname in dbplayer.nicknames:
        dbplayer.nicknames.append(dbnickname)
    if not dbhost in dbplayer.hosts:
        dbplayer.hosts.append(dbhost)

    dbsession = DBSession(player=dbplayer, server=dbserver)
    server.session.add(dbsession)

    server.session.commit()

"""
map = Column(String)
    teams = relationship('DBTeam', secondary=games2teams_table)
    complete = Column(Boolean)
    mode = Column(Enum('ffa', 'ball', 'tbd', 'tdm', '1bd', '1de', '1dm', name='mode', create_type=False))
    notes = relationship('DBNote')
    created = Column(DateTime, default=datetime.now) #started
    duration = Column(Integer) #seconds close enough
    server_id = Column(Integer, ForeignKey('servers.id'))
    server = relationship('DBServer')
"""



@transaction
def create_game(game, server, re_event):
    """
    {"port":27278,"participantStatsByName":{"Crashes":[2,0,2,3,1,2,3],"Kills":[2,1,5,3,4,1,5],"Longest Life":[67,26,72,61,66,66,38],"Ball Possession Time":[0,0,0,0,0,0,0],"Goals Scored":[0,0,0,0,0,0,0],"Damage Received":[740,0,620,880,770,690,810],"Assists":[4,0,1,5,3,4,0],"Experience":[105,35,201,191,179,86,197],"Damage Dealt":[420,30,360,350,380,410,290],"Goals Assisted":[0,0,0,0,0,0,0],"Damage Dealt to Enemy Buildings":[0,0,1040,1570,0,0,1000],"Deaths":[5,0,5,6,5,6,7],"Multikill":[0,0,0,2,2,0,3],"Kill Streak":[1,1,2,2,2,1,4]},"winnerByAward":{"Most Helpful":3,"Best Kill Streak":6,"Longest Life":2,"Most Deadly":2,"Best Multikill":6},"time":5200363,"type":"roundEnd","participants":[0,1,2,3,4,5,6]}
    """

    #update each player
    #create each team
    #create the game
    for team in game.teams:
        for player in team.player:
            #update the player with win/loss/drop/kills, etc
            pass

    server = server.session.query(DBServer).filter_by(port=server.port).first()
    now = datetime.now()

@transaction
def client_remove(player, server, event):
    dbsession = server.session.query(DBSession).filter_by(player_id=player.vaporId, active=True).first()
    now = datetime.now()
    dbsession.logout = now
    dbsession.duration = (now - dbsession.login).seconds
    dbsession.active = False
    dbsession.reason_closed = event['reason']
    server.session.commit()


@transaction
def update_player_stats(player, server, event):
    """
    {'plane': 'Explodet', 'stats': {'Crashes': 0, 'Kills': 0, 'Longest Life': 0, 'Ball Possession Time': 0, 'Goals Scored': 0, 'Damage Received': 100.41283, 'Assists': 1, 'Experience': 4, 'Damage Dealt': 0, 'Goals Assisted': 0, 'Damage Dealt to Enemy Buildings': 0, 'Deaths': 1, 'Multikill': 0, 'Kill Streak': 0}, 'port': 27286, 'perkGreen': 'Heavy Armor', 'perkRed': 'Director', 'skin': 'No Skin', 'team': 7, 'time': 52997, 'type': 'despawn', 'perkBlue': 'Reverse Thrust', 'player': 22}
    """

    dbplayer = server.session.query(DBPlayer).get(player.vaporId)

    estats = event['stats']
    time_played = (int(event['time']) - player.spawn_time)//1000

    found = False
    for stats in dbplayer.playerstats:
        if stats.server.port == event['port']:
            found = True
            #update the stats
            stats.time_played += time_played
            stats.crashes += estats['Crashes']
            stats.kills += estats['Kills']
            stats.assists += estats['Assists']
            stats.deaths += estats['Deaths']
            stats.goals += estats['Goals Scored']
            stats.goal_assists += estats['Goals Assisted']
            stats.ball_possession_time += estats['Ball Possession Time']
            stats.experience += estats['Experience']
            stats.damage_dealt += estats['Damage Dealt']
            stats.damage_received += estats['Damage Received']
            stats.damage_to_buildings += estats['Damage Dealt to Enemy Buildings']

            if event['plane'] == 'Loopy':
                stats.loopy_time += time_played
            elif event['plane'] == 'Bomber':
                stats.bomber_time += time_played
            elif event['plane'] == 'Explodet':
                stats.explodet_time += time_played
            elif event['plane'] == 'Biplane':
                stats.biplane_time += time_played
            elif event['plane'] == 'Miranda':
                stats.miranda_time += time_played

            if server.game.mode == GameMode.BALL:
                stats.ball_time += time_played
            elif server.game.mode == GameMode.TBD:
                stats.tbd_time += time_played
            elif server.game.mode == GameMode.FFA:
                stats.ffa_time += time_played

    if not found:
        #create the record
        dbserver = server.session.query(DBServer).filter(DBServer.port == event['port']).first()
        stats = DBPlayerStats(player_id = dbplayer.vapor_id,
                              server_id = dbserver.id,
                              time_played = time_played,
                              crashes = estats['Crashes'],
                              kills = estats['Kills'],
                              assists = estats['Assists'],
                              deaths = estats['Deaths'],
                              goals = estats['Goals Scored'],
                              goal_assists = estats['Goals Assisted'],
                              ball_possession_time = estats['Ball Possession Time'],
                              experience = estats['Experience'],
                              damage_dealt = estats['Damage Dealt'],
                              damage_received = estats['Damage Received'],
                              damage_to_buildings = estats['Damage Dealt to Enemy Buildings'],
                              )

        for plane in ('Loopy', 'Bomber', 'Explodet', 'Biplane', 'Miranda'):
            if event['plane'] == plane:
                setattr(stats, plane.lower()+'_time', time_played)
            else:
                setattr(stats, plane.lower()+'_time', 0)

        for item in ((GameMode.BALL, stats.ball_time),
                     (GameMode.TBD, stats.tbd_time),
                     (GameMode.FFA, stats. ffa_time),
                    ):
            mode, stat = item
            if server.game.mode is mode:
                stat = time_played
            else:
                stat = 0

        dbplayer.playerstats.append(stats)

    server.session.commit()


def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance
