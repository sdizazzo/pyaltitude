from .model import *




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



@transaction
def client_remove(player, server, event):
    dbsession = server.session.query(DBSession).filter_by(player_id=player.vaporId, active=True).first()
    now = datetime.now()
    dbsession.logout = now
    dbsession.duration = (now - dbsession.login).seconds
    dbsession.active = False
    dbsession.reason_closed = event['reason']
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
