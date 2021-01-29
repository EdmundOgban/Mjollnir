from enum import Enum, auto


class MsgType(Enum):
    REGULAR = auto()
    ACTION = auto()
    CTCP = auto()
    CTCPREPLY = auto()
    NOTICE = auto()
    NUMERIC = auto()
    SERVERCMD = auto()
    CLIENTCMD = auto()
    ALL = auto()
