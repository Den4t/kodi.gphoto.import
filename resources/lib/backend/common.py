import re
from __main__ import log

class CamFile(object):
    '''Base class for camera file object'''
    def __init__(self, *args, **kwargs):
        log('>>>> %s __init__'%self.__class__.__name__)
        self._type=None

    @property
    def _info(self):
        pass

    @property
    def type(self):
        if self._type is None:
            m=re.match(r'^([^/]+)/.*', self.mimetype, re.IGNORECASE)
            self._type=m.group(1)
        return self._type
