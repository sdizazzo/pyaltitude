from . import base

from aiologger import Logger

class Team(base.Base):
    logger = Logger.with_default_handlers(name='pyaltitude.Team')
    pass
