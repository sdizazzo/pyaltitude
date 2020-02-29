import os
import struct
import lzma
import logging
import xml.etree.ElementTree as ET

from . import base
from . import enums


map_dir = "/home/sean/altitude/maps"

logger = logging.getLogger(__name__)

class SpawnPoint(base.Base):
    logger = logging.getLogger('pyaltitude.SpawnPoint')

    def __init__(self):
        self.team = None

    
    #it's not really json...
    def parse(self, json):
        self._json = json
        logger.debug("Initialized SpawnPoint")
        super().parse(json, convert_types=True)

        return self
        


class Map(base.Base):
    logger = logging.getLogger('pyaltitude.Map')

    def __init__(self, server, name):
        self.server = server
        self.name = name
        self.path = os.path.join(map_dir, name+ '.altx')

        self.leftTeam = None
        self.rightTeam = None

        self.teams = list() #??  Where does teams go ??
        self.spawn_points = list()

        self.state = enums.MapState.INITIALIZED

        self.game_start = 0


    def parse_alte(self):
        self.state = enums.MapState.LOADING
        self.raw_xml = self._extract_xml()
        self._parse_map()
        self.state = enums.MapState.READY


    def _parse_map(self):
        
        #
        #just grab the spawnPoints so far...
        #
        logger.debug("Parsing map xml")
        root = ET.fromstring(self.raw_xml)
        for xspawn in root.iter("spawnPoints"):
            if not xspawn.attrib: continue

            sp = SpawnPoint()
            # <spawnPoints layer="1" x="194" y="580" orientation="0.0">
            #but then passed in as a dict
            sp.parse(xspawn.attrib)
            team = xspawn.find('team')
            sp.team = int(team.attrib['index'])
            
            self.spawn_points.append(sp)
    
    
    def _extract_xml(self):
        """
            Thanks to Biell for his documentaion of the map archive format.
            https://github.com/biell/alti-server/blob/78b1a60e05c2f5e3e674acefd88a0f574a8f83c1/altx-tool#L166
        """
        logger.debug('Extracting map xml from .altx file: %s' %  self.path)
        with lzma.open(self.path, 'rb') as fi:
            count = struct.unpack('<i', fi.read(4))[0]
            

            files = list()
            for i in range(count):
                length = struct.unpack_from('<h', fi.read(2), offset=0)[0]
                data = fi.read(length)
            
            alte_length = None
            for i in range(count):
                length = struct.unpack('<i', fi.read(4))[0]
                if not i:
                    alte_length = length
            
            # assume its the first file every time
            return fi.read(alte_length)


    def parse(self, json):
        self._json = json
        super().parse(json)
        self.name = self.map
        self.game_start = self.time
        logger.info("Loaded map %s on %s" % (self.name, self.server.serverName))
        return self

