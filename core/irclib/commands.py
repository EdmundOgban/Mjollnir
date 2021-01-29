import re

from ..enums import MsgType
from ..mixins import IRCMsg


def identify(identity):
    out = [IRCMsg(
            type=MsgType.SERVERCMD,
            command="USER",
            args=[identity["ident"], "0", "*", identity["realname"]],
    )]
    if "serverpw" in identity:
        out.append(IRCMsg(
            type=MsgType.SERVERCMD,
            command="PASS",
            args=[identity["serverpw"]]
        ))

    return out


def msg(to, text):
    return IRCMsg(type=MsgType.REGULAR, recipient=to, args=[to, text], text=text)


def action(to, text):
    return IRCMsg(type=MsgType.CTCP, ctcp="ACTION", recipient=to, args=[to, text], text=text)


def notice(to, text):
    return IRCMsg(type=MsgType.NOTICE, recipient=to, args=[to, text], text=text)


def ctcp(to, ctcpname, text=None):
    args = [to]
    if text:
        args.append(text)

    return IRCMsg(type=MsgType.CTCP, ctcp=ctcpname, recipient=to, args=args)


def ctcpreply(to, ctcpname, text=None):
    args = [to]
    if text:
        args.append(text)

    return IRCMsg(type=MsgType.CTCPREPLY, ctcp=ctcpname, recipient=to, args=args)


def join(channel, key=None):
    args = [channel]
    if key:
        args.append(key)

    return IRCMsg(type=MsgType.SERVERCMD, command="JOIN", args=args)


def joins(channels, keys=None):
    args = [",".join(channels)]
    if keys:
        args.append(",".join(keys))

    return IRCMsg(type=MsgType.SERVERCMD, command="JOIN", args=args)


def part(channel):
    return IRCMsg(type=MsgType.SERVERCMD, command="PART", args=[channel])


def parts(channels):
    return IRCMsg(type=MsgType.SERVERCMD, command="PART", args=[",".join(channels)])


def quit(reason=""):
    return IRCMsg(type=MsgType.SERVERCMD, command="QUIT", args=[reason])


def nick(newnick):
    return IRCMsg(type=MsgType.SERVERCMD, command="NICK", args=[newnick])


def mode(recipient, mode=None, text=None):
    args = [recipient]
    if mode:
        args.append(mode)

    if text:
        args.append(text)

    return IRCMsg(type=MsgType.SERVERCMD, command="MODE", args=args)


def kick(chan, nick, reason=None):
    args = [chan, nick]
    if reason:
        args.append(reason)

    return IRCMsg(type=MsgType.SERVERCMD, command="KICK", args=args)


def whois(nick):
    return IRCMsg(type=MsgType.SERVERCMD, command="WHOIS", args=[nick])


def pong(daemon, daemon2=None):
    args = [daemon]
    if daemon2:
        args.append(daemon2)

    return IRCMsg(type=MsgType.SERVERCMD, command="PONG", args=args)
