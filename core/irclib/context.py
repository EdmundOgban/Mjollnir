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

    def _reply(self, text, *, action=False):
        if action:
            factory = commands.action
        else:
            factory = commands.msg

        recipient = self.to(self.incoming)
        msg = factory(recipient, text)
        self.responses.append(msg)

    def reply(self, text):
        self._reply(text)

    def reply_action(self, text):
        self._reply(text, action=True)

    def msg(self, to, text):
        msg = commands.msg(to, text)
        self.responses.append(msg)

    def action(self, to, text):
        msg = commands.msg(to, text)
        self.responses.append(msg)

    def notice(self, to, text):
        msg = commands.notice(to, text)
        self.responses.append(msg)

    def ctcp(self, to, ctcpname, text=None):
        msg = commands.ctcp(to, ctcpname, text)
        self.responses.append(msg)

    def ctcpreply(self, to, ctcpname, text=None):
        msg = commands.ctcpreply(to, ctcpname, text)
        self.responses.append(msg)

    def raw(self, cmd, args):
        msg = IRCMsg(type=MsgType.SERVERCMD, command=cmd, args=args)
        self.responses.append(msg)

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

    def nickcmp(self, a, b):
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
