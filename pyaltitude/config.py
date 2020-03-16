
import os
import logging

import xml.etree.ElementTree as ET

from pyaltitude.server import Server, ServerLauncher

import yaml


logger = logging.getLogger(__name__)



class Config(object):

    def __init__(self, conf):
        self.conf_path = os.path.abspath(conf)
        logger.info('Reading config file: %s' % self.conf_path)
        with open(self.conf_path, 'rt') as fi: 
            filecnf = yaml.safe_load(fi)

        self.root = filecnf['root']
        logger.info('Set Altitude root: %s' % self.root)
        self.log_path = os.path.join(self.root, 'servers', 'log.txt')
        logger.info("Set log.txt: %s" % self.log_path)
        self.command_path = os.path.join(self.root, 'servers', 'command.txt')
        logger.info("Set command.txt: %s" % self.command_path)
        self.launcher_path = os.path.join(self.root, 'servers', 'launcher_config.xml')
        logger.info("Set launcher_config.xml: %s" % self.launcher_path)
        self.map_dir = os.path.join(self.root, 'maps')
        logger.info("Set map directory: %s" % self.map_dir)
        
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


    ####################
    # helper methods
    ####################

    def get_server(self, port):
        return self.server_launcher.server_for_port(port)

