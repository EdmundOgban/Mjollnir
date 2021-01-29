from ..enums import MsgType
from ..irclib import commands
from .. import utils
from . import numerics, clientcmds


class Bookkeeper:
    def __init__(self, network):
        self.network = network

    async def _manage_servercmd(self, msg):
        if msg.command == "PING":
            await utils.send(self.network, commands.pong(*msg.args))

    async def _manage_clientcmd(self, msg):
        if msg.command == "MODE":
            if msg.recipient == self.network.identity["nick"]:
                await clientcmds.umode(self.network, msg.args[-1])
            else:
                await clientcmds.cmode(self.network, msg.sender, msg.args)
        else:
            f = getattr(clientcmds, msg.command.lower(), None)
            if f:
                await f(self.network, msg)

    async def _manage_numeric(self, msg):
        f = getattr(numerics, f"numeric_{msg.command}", None)
        if f:
            await f(self.network, msg)

    async def manage(self, msg):
        if msg.type is MsgType.SERVERCMD:
            await self._manage_servercmd(msg)
        elif msg.type is MsgType.CLIENTCMD:
            await self._manage_clientcmd(msg)
        elif msg.type is MsgType.NUMERIC:
            await self._manage_numeric(msg)
