from . import base
from aiologger import Logger

class Map(base.Base):
    logger = Logger.with_default_handlers(name='pyaltitude.Map')

    def __init__(self, server):
        self.server = server

    async def parse(self, json):
        self._json = json
        await super().parse(json)

        self.name = self.map

        return self

