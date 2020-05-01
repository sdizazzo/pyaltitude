#!/usr/bin/env python3.7

import subprocess, logging


logger = logging.getLogger(__name__)


class Commands(object):

    def __init__(self, config):
        self.command_path = config.command_path
        self.cmd = "%s,console," % self.port

        #NOTE You can also send a `27283,restart` command, or perhaps
        #`-1,restart` to restart the server
        # not sure how it works, but noticed it browsing through the code

    def _send(self, cmd_name, *args):
        this_cmd = self.cmd[:]
        this_cmd += cmd_name
        for arg in args:
            this_cmd += ' '+str(arg)

        cmd = '/bin/echo "%s" >> %s' % (this_cmd, self.command_path)
        logger.debug('Executing "%s"' % cmd)
        subprocess.run(cmd, shell=True)

    def listPlayers(self):
        self._send('listPlayers')

    def serverWhisper(self, player, message):
        if player.is_bot(): return
        self._send('serverWhisper', player.nickname.replace(' ', '\ '), message)

    def serverMessage(self, message):
        self._send('serverMessage', message)

    def changeMap(self, map):
        self._send('changeMap', map)

    def applyForce(self, player, x, y):
        self._send('applyForce', player.player, x, y)

    def assignTeam(self, player, team):
        self._send('assignTeam', player.nickname.replace(' ', '\ '), team)

    def balanceTeams(self):
        self._send('balanceTeams')

    def testGravityMode(self, mode):
        self._send('testGravityMode', mode)

    def testCameraViewScale(self, scale):
        self._send('testCameraViewScale', scale)

    def overrideSpawnPoint(self, player, x, y, angle):
        self._send('overrideSpawnPoint', player.nickname.replace(' ', '\ '), x, y, angle)

    def overrideBallScore(self, leftscore, rightscore):
        self._send('overrideBallScore', leftscore, rightscore)

    def serverRequestPlayerChangeServer(self, player, ip, port, secret_code=None):
        #does it work?!
        ip = ip +':'+str(port)
        self._send('serverRequestPlayerChangeServer', player.nickname.replace(' ', '\ '), ip, secret_code or 'null')

    def drop(self, player):
        #TODO
        #if player.is_admin:
        #    raise SomeError('Server administrators cannot be dropped')
        self._send('drop', player.nickname.replace(' ', '\ '))

