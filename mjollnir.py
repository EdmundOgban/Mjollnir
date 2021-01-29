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

    if msg.command == "372":
        log.info(f"[MOTD@{network}] {msg.args[-1]}")
    elif msg.command == "NOTICE":
        pfx = f"{msg.nick}@{network}->{recipient}"

        if msg.type is MsgType.CTCPREPLY:
            log.info(f"CTCP Reply:{pfx} {' '.join(args)}")
        else:
            log.info(f"Notice:{pfx} {' '.join(args)}")
    elif msg.command == "PRIVMSG":
        if msg.type is MsgType.CTCP:
            log.info(f"CTCP:<{msg.nick}->{msg.recipient}@{network}> {' '.join(args)}")
        else:
            log.info(f"<{msg.nick}->{msg.recipient}@{network}> {' '.join(args)}")
    elif msg.command == "JOIN":
        channel = msg.args[0]
        if msg.nick == identity["nick"]:
            log.info(f"Joining {channel}@{network}")
        else:
            log.info(f"{msg.nick} joined {channel}@{network}")
    elif msg.command == "PART":
        try:
            channel, reason = msg.args
        except ValueError:
            channel, reason = msg.args[0], ""

        if msg.nick == identity["nick"]:
            log.info(f"Leaving {channel}@{network} ({reason})")
        else:
            log.info(f"{msg.nick} left {channel}@{network} ({reason})")
    elif msg.command == "MODE":
        if msg.nick == recipient:
            pfx = f"{msg.nick}@{network}"
        else:
            pfx = f"{msg.nick}->{recipient}@{network}"

        log.info(f"{pfx} sets mode: {' '.join(args)}")
    else:
    #elif msg.type is not MsgType.NUMERIC and msg.command != "PING":
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
        "modes"   : "+ixw"
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