import logging

from ..irclib import commands
from ..mixins import Nick
from .. import utils
from . import clientcmds


log = logging.getLogger("mjollnir")


def isupport_chanmodes(network, v, remove):
    try:
        A, B, C, D = v.split(",", 3)
    except ValueError:
        log.warning(f"!!! Network {network.name} is not declaring CHANMODES")
        A, B, C, D = '', '', '', ''
    else:
        if ',' in D:
            D, _ = D.split(",", 1)

    network.chanmodes = (set(A), set(B), set(C), set(D))


def isupport_prefix(network, v, remove):
    modes, literals = v.split(")", 1)
    modes = modes[1:]
    network.prefix_modes = modes
    network.prefix_literals = literals


def isupport_excepts(network, v, remove):
    network.excepts_mode = v or "e"


def isupport_modes(network, k, remove):
    network.maxmodes = int(k)


def isupport_targmax(network, v, remove):
    for pair in v.split(","):
        try:
            cmd, number = pair.split(":")
        except ValueError:
            pass
        else:
            network.targmax[cmd.upper()] = int(number or -1)


ISUPPORT = {
    "CHANMODES": isupport_chanmodes,
    "PREFIX": isupport_prefix,
    "EXCEPTS": isupport_excepts,
    "MODES": isupport_modes,
    "TARGMAX": isupport_targmax,
}


# RPL_WELCOME
async def numeric_001(network, msg):
    me = network.identity["nick"]
    modes = network.identity.get("modes")
    if modes:
        await utils.send(network, commands.mode(me, modes))


async def numeric_005(network, msg):
    for arg in msg.args[1:-1]:
        k, v = "", None
        try:
            k, v = arg.split("=", 1)
        except ValueError:
            k = arg

        if k.startswith("-"):
            remove = True
            k = k[1:]
            if k in network.capabilities:
                network.capabilities.pop(k)
        else:
            remove = False
            network.capabilities[k] = v

        f = ISUPPORT.get(k)
        if f:
            f(network, v, remove=remove)


async def numeric_324(network, msg):
    await clientcmds.cmode(network, msg.sender, msg.args[1:])


async def numeric_332(network, msg):
    channel, topictext = msg.args[-2:]
    channel = channel.lower()
    network.channels[channel].topic["text"] = topictext


async def numeric_333(network, msg):
    channel, setby, timestamp = msg.args[-3:]
    channel = channel.lower()
    topic = network.channels[channel].topic
    topic["setby"] = setby
    topic["timestamp"] = timestamp


async def numeric_353(network, msg):
    channel, nicks = msg.args[-2:]
    channel = channel.lower()
    for nk in nicks.split(" "):
        grade = set()
        for idx, c in enumerate(nk):
            try:
                modeidx = network.prefix_literals.index(c)
            except ValueError:
                nk = nk[idx:]
                break
            else:
                grade.add(network.prefix_modes[modeidx])

        nick = Nick(nk)
        nick.grade.update(grade)
        network.channels[channel].nicks[nk] = nick


async def numeric_367(network, msg):
    channel = msg.args[-4].lower()
    target, setby, timestamp = msg.args[-3:]
    network.channels[channel].bans[target] = (setby, timestamp)


async def numeric_376(network, msg):
    channels = network.identity["autojoin"]
    nopw = []
    withpw = []
    passwd = []
    for channel in channels:
        if isinstance(channel, tuple):
            if len(channel) == 2:
                ch, pw = channel
                withpw.append(ch)
                passwd.append(pw)
        else:
            nopw.append(channel)

    if nopw:
        await utils.send(network, commands.joins(nopw))

    if withpw:
        await utils.send(network, commands.joins(withpw, passwd))
