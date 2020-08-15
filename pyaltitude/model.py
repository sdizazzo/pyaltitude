
from datetime import datetime


from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, DateTime
from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import UUID


Base = declarative_base()


players2teams_table = Table('players2teams', Base.metadata,
    Column('player_vapor_id', UUID(as_uuid=True), ForeignKey('players.vapor_id')),
    Column('team_id', Integer, ForeignKey('teams.id'))
)


games2teams_table = Table('games2teams', Base.metadata,
    Column('game_id', Integer, ForeignKey('games.id')),
    Column('team_id', Integer, ForeignKey('teams.id'))
)


players2games_table = Table('players2games', Base.metadata,
    Column('player_vapor_id', UUID(as_uuid=True), ForeignKey('players.vapor_id')),
    Column('game_id', Integer, ForeignKey('games.id')),
    Column('game_dropped', Boolean, default=False)
)


players2hosts_table = Table('players2hosts', Base.metadata,
    Column('player_vapor_id', UUID(as_uuid=True), ForeignKey('players.vapor_id')),
    Column('host_id', Integer, ForeignKey('hosts.id'))
)

class DBServer(Base):
    __tablename__ = 'servers'
    id = Column(Integer, primary_key=True)
    port = Column(Integer) #, unique=True) TODO
    name = Column(String)
    created = Column(DateTime, default=datetime.now)


class DBTeam(Base):
    __tablename__ = 'teams'
    id = Column(Integer, primary_key=True)
    #all players that ever were on the team
    players = relationship('DBPlayer', secondary=players2teams_table)
    score = Column(Integer, default=0)
    win = Column(Boolean, default=False)
    mvp_id = Column(UUID(as_uuid=True), ForeignKey('players.vapor_id'))
    mvp = relationship('DBPlayer', uselist=False)
    dropped_players = relationship('DBPlayer')
    created = Column(DateTime, default=datetime.now)


class DBGame(Base):
    __tablename__ = 'games'
    id = Column(Integer, primary_key=True)
    map = Column(String)
    teams = relationship('DBTeam', secondary=games2teams_table)
    complete = Column(Boolean)
    mode = Column(Enum('ffa', 'ball', 'tbd', 'tdm', '1bd', '1de', '1dm', name='mode', create_type=False))
    notes = relationship('DBNote')
    created = Column(DateTime, default=datetime.now) #started
    duration = Column(Integer) #seconds close enough
    server_id = Column(Integer, ForeignKey('servers.id'))
    server = relationship('DBServer')


class DBNote(Base):
    __tablename__ = 'notes'
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey('games.id'))
    taken_by_id = Column(UUID(as_uuid=True), ForeignKey('players.vapor_id'))
    taken_by = relationship('DBPlayer', uselist=False)
    #TODO?? GET THE DEFAULT TIME FROM config.py to match with Nimbly
    created = Column(DateTime, default=datetime.now)
    text = Column(String)


#class Stats(Base):
#    __tablename__ = 'stats'


class DBHost(Base):
    __tablename__ = 'hosts'
    id = Column(Integer, primary_key=True)
    address = Column(String)
    players = relationship('DBPlayer', secondary=players2hosts_table, back_populates="hosts")
    created = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return "<DBHost(address='%s', players='%s', created='%s' )>" % (self.address, [p.vapor_id for p in self.players], self.created)


class DBNickname(Base):
    __tablename__ = 'nicknames'
    id = Column(Integer, primary_key=True)
    nickname = Column(String)
    player_id = Column(UUID(as_uuid=True), ForeignKey('players.vapor_id'))
    player = relationship('DBPlayer', uselist=False)
    created = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return "<DBNickname(nickname='%s', player='%s', created='%s' )>" % (self.nickname, self.player, self.created)


class DBSession(Base):
    __tablename__ = 'sessions'
    id = Column(Integer, primary_key=True)
    player_id = Column(UUID(as_uuid=True), ForeignKey('players.vapor_id'))
    player = relationship('DBPlayer', uselist=False)
    login = Column(DateTime, default=datetime.now)
    logout = Column(DateTime)
    server_id = Column(Integer, ForeignKey('servers.id'))
    server = relationship('DBServer', uselist=False)
    active = Column(Boolean, default=True)
    duration = Column(Integer)
    reason_closed = Column(String)

    def __repr__(self):
        return "<DBSession(player='%s', server='%s', active='%s', login='%s', duration='%s' why_closed='%s')>" % ( self.player.nicknames[0].nickname, self.server.name, self.active, self.login, self.duration, self.reason_closed)



class DBPlayerStats(Base):
    __tablename__ = 'playerstats'
    id = Column(Integer, primary_key=True)
    player_id = Column(UUID(as_uuid=True), ForeignKey('players.vapor_id'))
    player = relationship("DBPlayer", back_populates="playerstats")
    server_id = Column(Integer, ForeignKey('servers.id'))
    server = relationship('DBServer', uselist=False)

    time_played = Column(Integer, default=0)
    games_played = Column(Integer, default=0)
    dropped_games = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)

#   update on each death
#   ~~~~~~~~~~~~~~~~~~~~
    kills = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    deaths = Column(Integer, default=0)
    crashes = Column(Integer, default=0)
    goals = Column(Integer, default=0)
    goal_assists = Column(Integer, default=0)
    ball_possession_time = Column(Integer, default=0)
    experience = Column(Integer, default=0)
    damage_dealt = Column(Integer, default=0)
    damage_received = Column(Integer, default=0)
    damage_to_buildings = Column(Integer, default=0)

    # Not sure how to add these...
    #multikill
    #kill streak

    # keep track of game type so we can calculate stats based on it
    tbd_time = Column(Integer, default=0)
    ball_time = Column(Integer, default=0)
    ffa_time = Column(Integer, default=0)

#   Keep a timer of each plane so we know their fav
#   ~~~~~~~~~~~~~~~~~~~~
    loopy_time = Column(Integer, default=0)
    bomber_time = Column(Integer, default=0)
    explodet_time = Column(Integer, default=0)
    biplane_time = Column(Integer, default=0)
    miranda_time = Column(Integer, default=0)

    def __repr__(self):
        return "<DBPlayerStats(time_played='%s', kills='%s', assists='%s', deaths='%s', crashes='%s', goals='%s', goal_assist='%s', ball_possession_time='%s', experience='%s', damage_dealt='%s', damage_received='%s', damage_to_buildings='%s')>" % (self.time_played, self.kills, self.assists, self.deaths, self.crashes, self.goals, self.goal_assists, self.ball_possession_time, self.experience, self.damage_dealt, self.damage_received, self.damage_to_buildings)


class DBPlayer(Base):
    __tablename__ = 'players'
    vapor_id = Column(UUID(as_uuid=True), primary_key=True)
    hosts = relationship('DBHost', secondary=players2hosts_table, back_populates="players")
    nicknames = relationship('DBNickname')
    games = relationship('DBGame', secondary=players2games_table)
    ranking = Column(Integer, default=0)
    created = Column(DateTime, default=datetime.now)
    #will return a list for different servers
    playerstats = relationship("DBPlayerStats", back_populates="player")

    def __repr__(self):
        return  "<DBPLayer(vapor_id='%s', nicknames='%s', ranking='%s', hosts='%s', created='%s', games='%s' )>" % ( self.vapor_id, [n.nickname for n in self.nicknames], self.ranking, [h.address for h in self.hosts], self.created, self.games)


if __name__ == "__main__":
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    # used psycopg2-binary library on my system because I couldnt upgrade liqpq past 9.1
    # so psycopg2 was stuck at 2.6 making it incompatible with python3
    engine = create_engine("postgresql+psycopg2://test_user:blahblahblah@localhost/test?host=/tmp", echo=False)
    #Base.metadata.create_all(engine)
    #sys.exit(1)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    games = session.query(DBGame).all()
    #for g in games:
    #    print(g)
    
    hosts = session.query(DBHost).all()
    for h in hosts:
    #    if len(h.players) >1:
        if h.address == '72.209.126.134': 
            print(h)
    #players = session.query(DBPlayer).all()
    #for p in players:
    #    if p.playerstats:
    #        for stat in p.playerstats:
    #            print(stat)
    #dbsessions = session.query(DBSession).all()
    #for d in dbsessions:
    #    print(d)

