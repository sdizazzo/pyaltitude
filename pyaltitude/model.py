
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
    Column('game_id', Integer, ForeignKey('games.id'))
)


players2hosts_table = Table('players2hosts', Base.metadata,
    Column('player_vapor_id', UUID(as_uuid=True), ForeignKey('players.vapor_id')),
    Column('host_id', Integer, ForeignKey('hosts.id'))
)

class DBServer(Base):
    __tablename__ = 'servers'
    id = Column(Integer, primary_key=True)
    port = Column(Integer)
    name = Column(String)
    created = Column(DateTime, default=datetime.now)


class DBTeam(Base):
    __tablename__ = 'teams'
    id = Column(Integer, primary_key=True)
    players = relationship('DBPlayer', secondary=players2teams_table)
    score = Column(Integer, default=0)
    win = Column(Boolean, default=False)
    mvp_id = Column(UUID(as_uuid=True), ForeignKey('players.vapor_id'))
    mvp = relationship('DBPlayer', uselist=False)
    partial_players = relationship('DBPlayer')
    created = Column(DateTime, default=datetime.now)


class DBGame(Base):
    __tablename__ = 'games'
    id = Column(Integer, primary_key=True)
    map = Column(String)
    teams = relationship('DBTeam', secondary=games2teams_table)
    #ffa, everybody on their own team?
    #...or...?
    complete = Column(Boolean)
    mode = Column(Enum('ffa', 'ball', 'tbd', 'tdm', '1bd', '1de', '1dm', name='mode', create_type=False))
    notes = relationship('DBNote')
    created = Column(DateTime, default=datetime.now)
    duration = Column(Integer)
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
        return "<DBNickname(nickname='%s', player='%s', created='%s' )>" % (self.address, self.player, self.created)

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


class DBPlayer(Base):
    __tablename__ = 'players'
    vapor_id = Column(UUID(as_uuid=True), primary_key=True)
    hosts = relationship('DBHost', secondary=players2hosts_table, back_populates="players")
    nicknames = relationship('DBNickname')
    games = relationship('DBGame', secondary=players2games_table)
    ranking = Column(Integer, default=0)
    created = Column(DateTime, default=datetime.now)

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
    players = session.query(DBPlayer).all()
    for p in players:
        print(p)
    dbsessions = session.query(DBSession).all()
    for d in dbsessions:
        print(d)
