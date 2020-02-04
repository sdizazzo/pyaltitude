#!/usr/bin/env python3.7

import subprocess

class Commands(object):

    def __init__(self):
        self.command_path = '/home/sean/altitude/servers/command.txt'
        #get the path from the config
        self.cmd = "%s,console," % self.port


    def _send(self, cmd_name, *args):
        this_cmd = self.cmd[:]
        this_cmd += cmd_name
        for arg in args:
            this_cmd += ' '+str(arg)

        cmd = '/bin/echo "%s" >> %s' % (this_cmd, self.command_path)
        subprocess.run(cmd, shell=True)#,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)

    def listPlayers(self):
        self._send('listPlayers')

    def serverWhisper(self, nick, message):
        self._send('serverWhisper', nick.replace(' ', '\ '), message)

    def serverMessage(self, message):
        self._send('serverMessage', message)

    def changeMap(self, map):
        self._send('changeMap', map)

    def applyForce(self, player, x, y):
        self._send('applyForce', player, x, y)

    def assignTeam(self, nick, team):
        self._send('asignTeam', nick, team)

    def balanceTeams(self):
        self._send('balanceTeams')

    def testGravityMode(self, mode):
        self._send('testGravityMode', mode)

    def testCameraViewScale(self, scale):
        self._send('testCameraViewScale', scale)

    def overrideSpawnPoint(self, nick, x, y, angle):
        self._send('overrideSpawnPoint', nick.replace(' ', '\ '), x, y, angle)

    def overrideBallScore(self, leftscore, rightscore):
        self._send('overrideBallScore', leftscore, rightscore)
