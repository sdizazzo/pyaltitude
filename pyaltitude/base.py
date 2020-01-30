import re
import pprint
pp = pprint.PrettyPrinter(indent=4)

from aiologger import Logger


class Base(object):
    logger = Logger.with_default_handlers(name='pyaltitude.Base')

    re_int= re.compile(r'^-?\d+$')
    re_float = re.compile(r'^-?\d+\.?\d*$')

    """
        Objects subclass from this and json responses will be populated as
        instance variables automatically after calling 
        `await super().parse(attrs)`

        No boilerplate!
    """
    async def parse(self, json_dict, convert_types=False):
        for k, v in json_dict.items():
            if convert_types:
                v = await self.convert_value(v)
            setattr(self, k, v)

    
    async def convert_value(self, v):
        if v == 'true':
            return True
        elif v == 'false':
            return False
        elif Base.re_int.match(v):
            return int(v)
        elif Base.re_float.match(v):
            return float(v)
        return v

    async def describe(self):
        return pp.pformat({k:v for k,v in self.__dict__.items() if k != '_json'})
