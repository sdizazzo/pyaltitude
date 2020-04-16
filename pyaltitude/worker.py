

import logging
#import inspect

from pyaltitude.events import Events


logger = logging.getLogger(__name__)

#class ClassPathAdapter(logging.LoggerAdapter):
#    # Add the event name to log entries
#    # wont work now because modules don't subclass from Worker
#    # keep it around for a while anyway
#    def process(self, msg, kwargs):
#        return '%s - %s' % (self.extra['classPath'], msg), kwargs

class Worker(Events):
    """
        Each worker has all of the default events on it and each module event
        is dynamically appended to it as well.
    """

    #log_classPath = ClassPathAdapter(logger,{'classPath':inspect.currentframe().f_back.f_code.co_name})

    def __init__(self, event, config, modules=None, thread_lock=None):
        self.event = event
        self.config = config
        self.modules = modules
        self.thread_lock = thread_lock


    def get_module_events(self, module):
        events = list()
        for func in dir(module):
            if callable(getattr(module, func)) and not func.startswith('__'):
                events.append(func)
        return events


    def attach_module(self, module):
        module.config = self.config
        module.thread_lock = self.thread_lock
        for func_name in self.get_module_events(module()):
            func = getattr(module(), func_name)
            setattr(self, func_name, func)


    def execute(self):
        for module in self.modules:
            self.attach_module(module)

        try:
            logger.debug("Processing event %s" % self.event)
            method = getattr(self, self.event['type'])
        except AttributeError as e:
            logger.debug(repr(NotImplementedError(self.event['type'])))
            return

        method(self.event)

