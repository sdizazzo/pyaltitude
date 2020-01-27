class Module(object):
    def __init__(self, *args, **kwargs):
        pass

class ServerModule(Module):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)


class GameModeModule(ServerModule):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)

class MapModule(ServerModule):
    def __init__(self,  *args, **kwargs):
        super().__init__(self, *args, **kwargs)

