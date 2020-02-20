import re
import pprint
pp = pprint.PrettyPrinter(indent=4)


class Base(object):

    re_int = re.compile(r'^-?\d+$')
    re_float = re.compile(r'^-?\d+\.?\d*$')

    """
        Objects subclass from this and json responses will be populated as
        instance variables automatically after calling 
        `super().parse(attrs)`

        No boilerplate!
    """
    def parse(self, json_dict, convert_types=False):
        #some attrs in the json dont belong on the object
        #add them to the ignored keys
        ignored_keys = ('type',)
        for k, v in json_dict.items():
            if k in ignored_keys: continue
            if convert_types:
                v = self.convert_value(v)
            setattr(self, k, v)

    
    def convert_value(self, v):
        if v == 'true':
            return True
        elif v == 'false':
            return False
        elif Base.re_int.match(v):
            return int(v)
        elif Base.re_float.match(v):
            return float(v)
        return v

    def describe(self):
        return pp.pformat({k:v for k,v in self.__dict__.items() if k != '_json'})
