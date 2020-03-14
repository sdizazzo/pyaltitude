
import os
import logging

import xml.etree.ElementTree as ET

from pyaltitude.server import Server, ServerLauncher

import yaml


logger = logging.getLogger(__name__)



class Config(object):

    def __init__(self, conf):
        self.conf_path = os.path.abspath(conf)

        with open(self.conf_path, 'rt') as fi: 
            filecnf = yaml.safe_load(fi)

        self.root = filecnf['root']
        self.log_path = os.path.join(self.root, 'servers', 'log.txt')
        self.command_path = os.path.join(self.root, 'servers', 'command.txt')
        self.launcher_path = os.path.join(self.root, 'servers', 'launcher_config.xml')
        self.map_dir = os.path.join(self.root, 'maps')
        
        self.modules = filecnf['modules']

        self.server_launcher = self._parse_launcher_config()


    def _parse_launcher_config(self):
        servers = dict()

        logger.info('Parsing server config file at: %s' % self.launcher_path)
        with open(self.launcher_path, 'rt') as f:
            contents = f.read()

        root = ET.fromstring(contents)
        server_launcher = ServerLauncher()
        server_launcher = server_launcher.parse(root.attrib)

        for server_config in root.iter("AltitudeServerConfig"):
            server = Server(config=self)
            server = server.parse(server_config.attrib)
            server_launcher.servers.append(server)

        #mapList = root.find('mapList')
        return server_launcher  

