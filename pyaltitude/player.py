import uuid
import asyncio

from . import base

from aiologger import Logger



class Player(base.Base):
    logger = Logger.with_default_handlers(name='pyaltitude.Player')

    def __init__(self, server):
        self.is_admin = False
        self.server = server
        self.x = -1
        self.y = -1
        self.team = None
        self.attached = False
        #{"powerup":"Ball","positionY":1050,"playerVelX":-4.4,"playerVelY":-3.7,"port":27278,"velocityX":0,"time":389501,"type":"powerupPickup","velocityY":0,"player":2,"positionX":2036}
        #{"powerup":"Ball","positionY":158.65,"port":27278,"velocityX":-4.41,"time":1054454,"type":"powerupUse","velocityY":3.65,"player":4,"positionX":1191.59}
        self.powerup = None

    async def parse(self, json):
        self._json = json
        await super().parse(json)
        self.vaporId = uuid.UUID(self.vaporId)
        # UNTESTED
        #if self.vaporId in self.server.admin_vaporIds:
        #    self.is_admin = True
        return self

    async def parse_playerInfoEv(self, json):
        for k, v in json.items():
            if not k in ('port', 'type', 'player'):
                setattr(self, k, v)

    def set_team(self, team):
        self.team = team

    async def whisper(self, message):
        await self.server.serverWhisper(self.nickname, message)

    async def applyForce(self, x, y):
        await self.server.applyForce(self.player, x, y)

    async def spawned(self):
        #reset our spawn point after a call to /attach
        if self.attached:
            await asyncio.sleep(1)
            await self.server.overrideSpawnPoint(self.nickname, 0, 0, 0)
        self.attached = False

    def is_alive(self):
        if self.team == 2 or (self.x, self.y) == (-1, -1)
            return False
        else:
            return True

    def is_bot(self):
        return int(self.vaporId) == 0

    def __eq__(self, other):
        return self.nickname == other.nickname

