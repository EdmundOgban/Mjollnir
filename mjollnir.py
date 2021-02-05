import locale
import logging
import math
import random
from functools import partial

import trio

from .core.bookkeeping.bookkeeping import Bookkeeper
from .core.irclib import commands
from .core.mixins import MessagePump, Network, IRCMsg
from .core.drivers import trio_driver
from .core.enums import MsgType
from .plugins import dispatcher
from . import vt100

locale.setlocale(locale.LC_ALL, '')
logging.basicConfig(format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S", level=logging.DEBUG)
log = logging.getLogger("mjollnir")


def console_reader(wsendq):
    recipient = None
    while True:
        text = input().strip()
        if text.startswith("#"):
            recipient = text
            print(f"Talking to {recipient}")
        elif text.startswith("/"):
            trio.from_thread.run(wsendq.send, f"{text[1:]}")
            print(f"RAW: {text[1:]}")
        elif recipient is not None and text:
            trio.from_thread.run(wsendq.send, commands.msg(recipient, text))
            print(f"To {recipient}: {text}")


async def console_print(identity, msg):
    network = identity["network"]
    recipient, *args = msg.args
    text = vt100.colorize(msg.args[-1])

    if msg.command == "001":
        log.info(f"@{network} {msg.args[-1]}")
    elif msg.command == "372":
        log.info(f"@{network} [MOTD] {text}")
    elif msg.command == "NOTICE":
        if msg.type is MsgType.CTCPREPLY:
            log.info(f"@{network} CTCPReply {msg.nick} {msg.ctcpname} {text}")
        else:
            log.info(f"@{network} -{msg.nick}->{msg.recipient}- {text}")
    elif msg.command == "PRIVMSG":
        if msg.type is MsgType.CTCP:
            log.info(f"@{network} CTCP {msg.nick}->{msg.recipient} {msg.ctcpname} {text}")
        elif msg.type is MsgType.ACTION:
            log.info(f"@{network} * {msg.nick}->{msg.recipient} {text}")
        else:
            log.info(f"@{network} <{msg.nick}->{msg.recipient}> {text}")
    elif msg.command == "JOIN":
        channel = msg.args[0]
        if msg.nick == identity["nick"]:
            log.info(f"@{network} Joining {channel}")
        else:
            log.info(f"@{network} {msg.nick} joined {channel}")
    elif msg.command == "PART":
        try:
            channel, reason = msg.args
        except ValueError:
            channel, reason = msg.args[0], None

        if msg.nick == identity["nick"]:
            log.info(f"@{network} Leaving {channel}" + f" ({reason})" if reason else "")
        else:
            log.info(f"@{network} {msg.nick} left {channel}" + f" ({reason})" if reason else "")
    elif msg.command == "QUIT":
        log.info(f"@{network} {msg.nick} has quit IRC ({msg.args[-1]})")
    elif msg.command == "MODE":
        if msg.nick == recipient:
            pfx = msg.nick
        else:
            pfx = f"{msg.nick}->{recipient}"

        log.info(f"@{network} {pfx} sets mode: {' '.join(args)}")
    elif msg.command != "PING" and msg.type != MsgType.NUMERIC:
        log.debug(f"@{identity['network']} {msg}")


class Mjollnir:
    def __init__(self):
        self.networks = {}
        self.nursery = None

    def add_network(self, identity):
        name = identity["network"]
        if name in self.networks:
            raise Exception("Network already present")

        wsendq, rsendq = trio.open_memory_channel(math.inf)
        driver = trio_driver.Driver(identity, rsendq, wsendq)
        self.networks[name] = Network(identity, driver)

    def spawn_network(self, network):
        bookkeeper = Bookkeeper(network)
        pluginmanager = dispatcher.Plugins(network)
        messagepump = MessagePump()
        messagepump.attach_source(network._driver.receive)
        messagepump.add_sink(bookkeeper.manage, [MsgType.ALL])
        messagepump.add_sink(pluginmanager.dispatch, [MsgType.ALL])
        messagepump.add_sink(partial(console_print, network.identity), [MsgType.ALL])
        self.nursery.start_soon(network._driver.spool)
        self.nursery.start_soon(network._driver.connect)
        self.nursery.start_soon(messagepump.run)
        if network.name == "Azzurra":
            run_sync = partial(trio.to_thread.run_sync, cancellable=True)
            self.nursery.start_soon(run_sync, console_reader, network._driver.wsendq)

    async def run(self):
        try:
            async with trio.open_nursery() as self.nursery:
                for network in self.networks.values():
                    self.spawn_network(network)
        except KeyboardInterrupt:
            for network in self.networks.values():
                await network._driver.disconnect("KeyboardInterrupt")
        finally:
            self.nursery = None


async def main():
    identity = {
        "nick"    : "Mjollnir",
        "altnick" : "Mjollnir`",
        "ident"   : "trio",
        "network" : "Azzurra",
        "servers" : [
            ("allnight.azzurra.org", 9999, True, False),
        ],
        "realname": "Mjollnir",
        "autojoin": [("#supybot", "mannaccia")], #, "#unity"],
        "modes"   : "+ixws"
    }

    identity2 = identity.copy()
    identity2["network"] = "EFNet"
    identity2["servers"] = [
        ("irc.efnet.nl", 6667, False, False)
    ]
    identity2["autojoin"] = [
        "#mjollnir"
    ]

    bot = Mjollnir()
    bot.add_network(identity)
    #bot.add_network(identity2)
    await bot.run()


if __name__ == '__main__':
    trio.run(main)