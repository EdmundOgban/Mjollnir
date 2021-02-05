from . import commands
from .. import utils
from ..mixins import IRCMsg, Nick
from ..enums import MsgType

MAP_RFC1459 = str.maketrans("{|}~", r"[\]^")
MAP_STRICT_RFC1459 = str.maketrans("{|}", r"[\]")


class IRCContext:
    def __init__(self, network):
        self.incoming = None
        self.network = network
        self.reset_responses()

    def _reply(self, text, *, action=False, notice=False):
        if action:
            factory = commands.action
        elif notice:
            factory = commands.notice
        else:
            factory = commands.msg

        if not isinstance(text, (bytearray, bytes)):
            text = str(text)

        recipient = self.to(self.incoming)
        msg = factory(recipient, text)
        self._enqueue(msg)

    def reply(self, text):
        self._reply(text)

    def reply_action(self, text):
        self._reply(text, action=True)

    def reply_notice(self, text):
        self._reply(text, notice=True)

    def msg(self, to, text):
        msg = commands.msg(to, text)
        self._enqueue(msg)

    def action(self, to, text):
        msg = commands.action(to, text)
        self._enqueue(msg)

    def notice(self, to, text):
        msg = commands.notice(to, text)
        self._enqueue(msg)

    def ctcp(self, to, ctcpname, text=None):
        msg = commands.ctcp(to, ctcpname, text)
        self._enqueue(msg)

    def ctcpreply(self, ctcpname, text=None):
        msg = commands.ctcpreply(self.incoming.nick, ctcpname, text)
        self._enqueue(msg)

    def raw(self, cmd, args):
        msg = IRCMsg(type=MsgType.SERVERCMD, command=cmd, args=args)
        self._enqueue(msg)

    def nick_tolower(self, nick):
        casing = self.network.capabilities["CASEMAPPING"]

        if casing == "rfc1459":
            return nick.translate(MAP_RFC1459).lower()
        elif casing == "strict-rfc1459":
            return nick.translate(MAP_STRICT_RFC1459).lower()
        elif casing == "ascii":
            return nick.lower()
        else:
            raise ValueError(f"Invalid CASEMAPPING '{casing}'")

    def nick_isin(self, nick, channel):
        for other in channel:
            if self.nick_cmp(nick, other):
                return True

        return False

    def nick_cmp(self, a, b):
        if isinstance(a, Nick):
            a = a.name
        elif not isinstance(a, str):
            return False

        if isinstance(b, Nick):
            b = b.name
        elif not isinstance(b, str):
            return False

        return self.nick_tolower(a) == self.nick_tolower(b)

    def in_channel(self):
        chantypes = self.network.capabilities["CHANTYPES"]
        return utils.ischannel(self.incoming.recipient, chantypes)

    def to(self, msg):
        chantypes = self.network.capabilities["CHANTYPES"]
        if utils.ischannel(msg.recipient, chantypes):
            return msg.recipient
        else:
            return msg.nick

    def set_message(self, msg):
        self.incoming = msg

    def reset_responses(self):
        self.responses = []

    def _enqueue(self, msg):
        identity = self.network.identity
        msg.nick = identity["nick"]
        msg.ident = identity["ident"]
        msg.hostname = self.network.hostname
        self.responses.append(msg)