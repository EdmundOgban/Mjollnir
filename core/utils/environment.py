from collections import defaultdict

from . import timestamp_now
from .singleton import Singleton


class Mores:
    def __init__(self):
        self.mores = {}

    def cleanup(self):
        self.mores = {identhost: v for identhost, v in self.mores.items()
            if timestamp_now() < v[1] + 3600}

    def __getitem__(self, identhost):
        more = self.mores.get(identhost)
        if more is not None:
            return more[0]

    def __setitem__(self, identhost, mores):
        self.mores[identhost] = (mores, timestamp_now())


class Env(metaclass=Singleton):
    def __init__(self):
        self._mores = defaultdict(Mores)

    def cleanup(self):
        for more in self._mores.values():
            more.cleanup()

    @property
    def mores(self):
        return self._mores
