#!/usr/bin/env python3.7

import asyncio

class Commands(object):

    def __init__(self):
        self.command_path = '/home/sean/altitude/servers/command.txt'
        #get the path from the config
        self.cmd = "%s,console," % self.port


    async def _send(self, cmd_name, *args):
        this_cmd = self.cmd[:]
        this_cmd += cmd_name
        for arg in args:
            this_cmd += ' '+str(arg)

        cmd = '/bin/echo "%s" >> %s' % (this_cmd, self.command_path)
        await asyncio.create_subprocess_shell(cmd)#,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)

    async def listPlayers(self):
        await self._send('listPlayers')

    async def serverWhisper(self, nick, message):
        await self._send('serverWhisper', nick.replace(' ', '\ '), message)

    async def serverMessage(self, message):
        await self._send('serverMessage', message)

    async def changeMap(self, map):
        await self._send('changeMap', map)

    async def applyForce(self, player, x, y):
        await self._send('applyForce', player, x, y)

    async def assignTeam(self, nick, team):
        await self._send('asignTeam', nick, team)

    async def balanceTeams(self):
        await self._send('balanceTeams')

    async def testGravityMode(self, mode):
        await self._send('testGravityMode', mode)

    async def testCameraViewScale(self, scale):
        await self._send('testCameraViewScale', scale)

    async def overrideSpawnPoint(self, player, x, y, angle):
        await self._send('overrideSpawnPoint', player, x, y, angle)

    async def overrideBallScore(self, leftscore, rightscore):
        await self._send('overrideBallScore', leftscore, rightscore)
