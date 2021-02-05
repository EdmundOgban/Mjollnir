import logging

from ..irclib import commands
from ..mixins import Channel, Nick
from .. import utils

log = logging.getLogger("mjollnir")


async def umode(network, modes):
    for sign, mode in utils.split_umodes(modes):
        if sign == "+":
            network.ownmodes.add(mode)
        else:
            network.ownmodes.remove(mode)


async def cmode(network, sender, args):
    ch = network.channels[args[0].lower()]

    if len(args) > 2:
        modes, targets = args[1], args[2:]
    else:
        modes, targets = args[1], ""

    A, B, C, D = network.chanmodes
    AB = A | B | set(network.prefix_modes)
    for sign, mode, target in utils.split_cmodes(modes, targets, AB, C, D):
        if mode == "b":
            if sign == "+":
                ch.bans[target] = (sender, utils.timestamp_now())
            else:
                try:
                    ch.bans.pop(target)
                except KeyError:
                    pass
        elif mode == network.excepts_mode:
            if sign == "+":
                ch.bans[target] = (sender, utils.timestamp_now())
            else:
                try:
                    ch.excepts.pop(target)
                except KeyError:
                    pass
        elif mode in network.prefix_modes:
            if sign == "+":
                ch.nicks[target].grade.add(mode)
            else:
                try:
                    ch.nicks[target].grade.remove(mode)
                except KeyError:
                    pass
        else:
            if sign == "+":
                ch.modes[mode] = target
            else:
                try:
                    ch.modes.pop(mode)
                except KeyError:
                    pass


async def join(network, msg):
    channel = msg.args[0].lower()
    if msg.nick == network.identity["nick"]:
        network.channels[channel] = Channel(channel)
        await utils.send(network, commands.mode(channel))
        await utils.send(network, commands.mode(channel, "+b"))
    else:
        network.channels[channel].nicks[msg.nick] = Nick(msg.nick)


async def part(network, msg):
    channel = msg.args[0].lower()
    if msg.nick == network.identity["nick"]:
        network.channels.pop(channel)
    else:
        network.channels[channel].nicks.pop(msg.nick)


async def quit(network, msg):
    for channel in network.channels.values():
        if msg.nick in channel:
            channel.nicks.pop(msg.nick)


async def nick(network, msg):
    newnick = msg.args[0]
    for channel in network.channels.values():
        nick = channel.nicks.get(msg.nick)
        if nick is not None:
            if msg.nick == network.identity["nick"]:
                network.identity["nick"] = newnick

            channel.nicks.pop(msg.nick)
            nick.rename(newnick)
            channel.nicks[newnick] = nick


async def topic(network, msg):
    channel = msg.args[0].lower()
    try:
        topictext = msg.args[1]
    except IndexError:
        topictext = ''

    topic = network.channels[channel].topic
    topic["text"] = topictext
    topic["setby"] = msg.nick
    topic["timestamp"] = utils.timestamp_now()
