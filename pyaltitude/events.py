import time
import logging
from datetime import datetime, timezone, timedelta, tzinfo

from pyaltitude.player import Player
from pyaltitude.map import Map
from pyaltitude.enums import MapState


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

    def sessionStart(self, event, INIT, thread_lock):
        #{'date': '2020 Feb 22 04:01:43:847 EST', 'port': -1, 'time': 0,'type': 'sessionStart'}
        date_str = event['date'][:-8]
        date = datetime.strptime(date_str, "%Y %b %d %H:%M:%S").replace(tzinfo=EST())
        logger.info("Session officially starts at (Nimbly time): %s" % date)
        for server in self.servers.values():
            server.start = date
            server.time = 0

    def serverInit(self, event, _, thread_lock):
        pass


    def clientAdd(self, event, INIT, thread_lock):
        server = self.servers[event['port']]
        player = Player(server)
        player = player.parse(event)
        server.add_player(player, message =not INIT)


    def clientRemove(self, event, INIT, thread_lock):
        server = self.servers[event['port']]

        # see https://github.com/sdizazzo/pyaltitude/issues/4
        player = server.get_player_by_vaporId(event['vaporId'])
        server.remove_player(player, event['reason'], event['message'], message =not INIT)


    def spawn(self, event, _, thread_lock):
        server = self.servers[event['port']]
        #{'plane': 'Biplane', 'port': 27280, 'perkGreen': 'Heavy Armor',
        #'perkRed': 'Heavy Cannon', 'skin': 'No Skin', 'team': 4, 'time':
        #18018150, 'type': 'spawn', 'perkBlue': 'Ultracapacitor', 'player': 2}
        player = server.get_player_by_number(event['player'])
        player.spawned()


    def logPlanePositions(self, event, _, thread_lock):
        server = self.servers[event['port']]
        server.map_player_positions(event)


    def mapLoading(self, event, _, thread_lock):
        server = self.servers[event['port']]
        #{'port': 27279, 'time': 16501201, 'type': 'mapLoading', 'map':'ffa_core'}
        # THis event gives us the map name which is enough to
        # instatiate the map object and begin parsing the map 
        # file for what we need:
        #    * right now just the spawn points so we can reset to them
        #      after an /attach to a player
        map_ = Map(server, event['map'])
        map_.parse_alte()
        server.map = map_


    def serverHitch(self, event, _, thread_lock):
        #{"duration":631.8807983398438,"port":27278,"time":3367621,"type":"serverHitch","changedMap":false}
        server = self.servers[event['port']]
        server.serverMessage('ServerHitch: %.2f' % event['duration'])
        logger.warning('ServerHitch: %.2f, %s' % (event['duration'], server.serverName))


    def roundEnd(self, event, _, thread_lock):
        pass


    def powerupUse(self, event, _, thread_lock):
        pass


    def powerupAutoUse(self, event, _, thread_lock):
        pass


    def powerupPickup(self, event, _, thread_lock):
        pass


    def mapChange(self, event, _, thread_lock):
        server = self.servers[event['port']]
        #{"mode":"ball","rightTeam":5,"port":27278,"leftTeam":6,"time":5808529,"type":"mapChange","map":"ball_cave"}

        wait = .5
        t = 0
        while not server.map.state == MapState.READY:
            time.sleep(wait)
            logger.warning('mapChange: Sleeping waiting for map to become available: %s' % server.map.name)
            t+=wait
            if t >= 2:
                logger.warning('mapChange: Took over 2 seconds to parse map.  Continued anyway...')
                break

        server.map.parse(event)
        server.map.state = MapState.ACTIVE


    def playerInfoEv(self, event, _, thread_lock):
        server = self.servers[event['port']]
        if event['leaving']: return             #<-----  That was all I needed for my player tracking problems!

        player = server.get_player_by_number(event['player'])
        player.parse_playerInfoEv(event)


    def teamChange(self, event, _, thread_lock):
        server = self.servers[event['port']]
        player = server.get_player_by_number(event['player'])
        player.team = event['team']


    def attach(self, server, from_player, to_player):
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


    def consoleCommandExecute(self, event, _, thread_lock):
        server = self.servers[event['port']]

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

