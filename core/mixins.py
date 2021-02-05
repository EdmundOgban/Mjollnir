import logging
import random
import string
from collections import defaultdict

from .enums import MsgType
from .irclib import commands

log = logging.getLogger("mjollnir")


class MessagePump:
    def __init__(self):
        self.source = None
        self.sinks = defaultdict(list)

    def attach_source(self, source):
        self.source = source

    def add_sink(self, cb, events):
        for event in events:
            if type(event) is MsgType:
                self.sinks[event].append(cb)

    def remove_sink(self, cb):
        self.sinks.pop(cb)

    async def run(self):
        if self.source is None:
            raise RuntimeError("No source attached")

        async for msg in self.source():
            for cb in self.sinks.get(msg.type, []):
                await cb(msg)

            for cb in self.sinks.get(MsgType.ALL, []):
                await cb(msg)


class Network:
    def __init__(self, identity, driver):
        self.identity = identity
        self._driver = driver
        self.ownmodes = set()
        self.chanmodes = set()
        self.excepts_mode = "e"
        self.prefix_modes = []
        self.prefix_literals = []
        self.capabilities = {}
        self.channels = {}

    @property
    def name(self):
        return self.identity["network"]

    @property
    def connected(self):
        return self._driver.connected

    def __contains__(self, other):
        return other == self.name

    def _nicknames(self):
        nick = self.identity["altnick"]
        while True:
            yield nick
            nick = "{}{:02}".format("".join(random.sample(string.ascii_letters, 7)),
                random.randint(0, 99))


class Channel:
    def __init__(self, channelname):
        self.name = channelname
        self.topic = dict(
            text='',
            setby='',
            timestamp=''
        )
        self.modes = {}
        self.nicks = {}
        self.bans = {}
        self.excepts = {}

    def __iter__(self):
        for nick in self.nicks:
            yield nick

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name.lower() == other.lower()
        elif isinstance(other, Channel):
            return self.name.lower() == other.name.lower()
        else:
            return False

    def __contains__(self, name):
        return name in self.nicks

    def __str__(self):
        return self.name


class Nick:
    def __init__(self, name):
        self.name = name
        self.ident = None
        self.hostname = None
        self.grade = set()

    def rename(self, newnick):
        self.name = newnick


def _ctcp(name, args=None):
    if args:
        return f"\x01{name} {args}\x01"
    else:
        return f"\x01{name}\x01"


def _join_args(args):
    L = []
    space_found = False
    for arg in map(str, args):
        if not space_found and " " in arg:
            L.append(f":{arg}")
            space_found = True
        else:
            L.append(arg)

    return " ".join(L) or None

# FIXME
def _join_args_bytes(args):
    L = []
    space_found = False
    for arg in args:
        if isinstance(arg, str):
            arg = arg.encode()

        if not space_found and b" " in arg:
            L.append(b":" + arg)
            space_found = True
        else:
            L.append(arg)

    return b" ".join(L) or None


class IRCMsg:
    def __init__(self, nick=None, ident=None, hostname=None, recipient=None,
        type=None, ctcp=None, command=None, args=None, text='', encoded=False):
        self.nick = nick
        self.ident = ident
        self.hostname = hostname
        self.recipient = recipient
        self.type = type
        self.ctcpname = ctcp
        self.command = command
        self.args = args or []
        self._text = text
        self.encoded = encoded

    def copy(self):
        return IRCMsg(self.nick, self.ident, self.hostname, self.recipient,
            self.type, self.ctcpname, self.command, self.args.copy(),
            self.text, self.encoded)

    @property
    def sender(self):
        if self.nick is None and self.ident is None and self.hostname is None:
            return

        if self.ident is None and self.hostname is None:
            return f"{self.nick}"
        else:
            return f"{self.nick}!{self.ident}@{self.hostname}"

    def __repr__(self):
        return ("<IRCMsg object at 0x{:X}, sender={}, recipient={}, type={},"
             " ctcpname={}, command={}, args={}>").format(
                 id(self), self.sender, self.recipient,
                 self.type, self.ctcpname, self.command,
                 self.args)

    def __str__(self):
        s = ""

        if self.type in (MsgType.ACTION, MsgType.CTCP, MsgType.CTCPREPLY):
            if self.type is MsgType.ACTION:
                ctcpname = "ACTION"
            else:
                ctcpname = self.ctcpname

            if len(self.args) > 1:
                ctcpbody = _ctcp(ctcpname, " ".join(self.args[1:]))
            else:
                ctcpbody = _ctcp(ctcpname)

            args = [self.args[0], ctcpbody]
        else:
            args = self.args

        args = _join_args(args)

        if self.type in (MsgType.REGULAR, MsgType.ACTION, MsgType.CTCP):
            s = f"PRIVMSG {args}"
        elif self.type in (MsgType.NOTICE, MsgType.CTCPREPLY):
            s = f"NOTICE {args}"
        elif self.type is MsgType.NUMERIC:
            s = f"{self.command} {args}"
        elif self.type is MsgType.SERVERCMD:
            if args:
                s = f"{self.command} {args}"
            else:
                s = self.command
        elif self.type is MsgType.CLIENTCMD:
            s = f":{self.sender} {self.command} {args}"

        return s

    # FIXME
    def __bytes__(self):
        s = bytearray()

        if self.type in (MsgType.ACTION, MsgType.CTCP, MsgType.CTCPREPLY):
            if self.type is MsgType.ACTION:
                ctcpname = "ACTION"
            else:
                ctcpname = self.ctcpname

            if len(self.args) > 1:
                ctcpbody = _ctcp(ctcpname, " ".join(self.args[1:]))
            else:
                ctcpbody = _ctcp(ctcpname)

            args = [self.args[0].encode(), ctcpbody.encode()]
        else:
            args = self.args

        args = _join_args_bytes(args)

        if self.type in (MsgType.REGULAR, MsgType.ACTION, MsgType.CTCP):
            s.extend(b"PRIVMSG ")
            s.extend(args)
        elif self.type in (MsgType.NOTICE, MsgType.CTCPREPLY):
            s.extend(b"NOTICE ")
            s.extend(args)
        elif self.type is MsgType.NUMERIC:
            s.extend(self.command.encode())
            s.extend(args)
        elif self.type is MsgType.SERVERCMD:
            s.extend(self.command)
            if args:
                s.extend(args)
        elif self.type is MsgType.CLIENTCMD:
            s = f":{self.sender} {self.command} {args}"

        return bytes(s)
