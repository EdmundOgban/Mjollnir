import logging
import re

from ..mixins import IRCMsg
from ..enums import MsgType


sender_re = re.compile(r'^(\S+)!(\S+)@(\S+)$')
ctcp_re = re.compile(
    r"^\x01"
    r"([^ \x00\x01\n\r]+) ?"
    r"([^\x00\x01\n\r]+)?"
    r"\x01$")

log = logging.getLogger("mjollnir")


def _split_hostmask(sender):
    nick, ident, hostname = (None, None, None)
    try:
        m = sender_re.match(sender)
        if m:
            nick, ident, hostname = m.groups()
        else:
            raise ValueError
    except ValueError:
        nick = sender
    except TypeError:
        pass

    return nick, ident, hostname


def _decode_command(line, ircmsg):
    cmd, text = (ircmsg.command, ircmsg.args[-1])

    if not line.startswith(":"):
        cmdtype = MsgType.SERVERCMD
    elif cmd.isdigit():
        cmdtype = MsgType.NUMERIC
    elif cmd == "NOTICE":
        m = ctcp_re.match(text)
        if m:
            cmdtype = MsgType.CTCPREPLY
            # Normalize to UPPERCASE
            ircmsg.ctcpname = m.group(1).upper()
            ircmsg.text = m.group(2) or ''
        else:
            cmdtype = MsgType.NOTICE
            ircmsg.text = text
    elif cmd == "PRIVMSG":
        m = ctcp_re.match(text)
        if m:
            # Normalize to UPPERCASE
            ctcpname = m.group(1).upper()
            if ctcpname == "ACTION":
                cmdtype = MsgType.ACTION
            else:
                cmdtype = MsgType.CTCP
                ircmsg.ctcpname = ctcpname

            ircmsg.text = m.group(2) or ''
        else:
            cmdtype = MsgType.REGULAR
            ircmsg.text = text
    else:
        cmdtype = MsgType.CLIENTCMD

    return cmdtype


def parse(line):
    ircmsg = IRCMsg()
    try:
        first, rest = line.split(" ", 1)
        if first.startswith(":"):
            ircmsg.command, rest = rest.split(" ", 1)
            ircmsg.nick, ircmsg.ident, ircmsg.hostname = _split_hostmask(first[1:])
        else:
            ircmsg.command = first

        # Normalize to UPPERCASE
        ircmsg.command = ircmsg.command.upper()

        while not rest.startswith(":"):
            try:
                arg, rest = rest.split(" ", 1)
            except ValueError:
                ircmsg.args.append(rest)
                break
            else:
                ircmsg.args.append(arg)
        else:
            ircmsg.args.append(rest[1:])

        ircmsg.type = _decode_command(line, ircmsg)
        if ircmsg.command in ("PRIVMSG", "NOTICE", "MODE") or ircmsg.command.isdigit():
            ircmsg.recipient = ircmsg.args[0]
    except ValueError:
        log.debug("parser.parse failed parsing message:\r\n '%s'", line)
        ircmsg.text = line

    return ircmsg
