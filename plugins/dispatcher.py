import inspect
import string
import logging
from random import randint

import trio

from ..core import utils
from ..core.irclib import commands
from ..core.irclib.context import IRCContext
from ..core.enums import MsgType
from ..core.mixins import IRCMsg, Nick
from .builtins import Builtins
from .nested import NestedScanner
from .spooler import Spooler

BOTCMD_PREFIX = ")"
VALID_CMDCHARS = string.ascii_letters + string.digits + "_"

log = logging.getLogger("mjollnir")


def validate_command(cmd):
    if not cmd or cmd[0].isdigit() or cmd[0] == "_":
        return False

    return "".join(c for c in cmd if c in VALID_CMDCHARS)


async def _spawn_sync(f, ctx, msg, args):
    if hasattr(f, "tags") and f.tags.get("threaded"):
        log.debug("_spawn_sync threaded")
        await trio.to_thread.run_sync(f, ctx, msg, args)
    else:
        log.debug("_spawn_sync non-threaded")
        f(ctx, msg, args)


async def _spawn_async(f, ctx, msg, args):
    if hasattr(f, "tags") and f.tags.get("threaded"):
        raise RuntimeError("You must not use async and threaded together.")
    else:
        log.debug("_spawn_async")
        await f(ctx, msg, args)


async def _spawn(ctx, methods, msg, cmd, args):
    f = methods.get(cmd)
    if f:
        if inspect.iscoroutinefunction(f):
            await _spawn_async(f, ctx, msg, args)
        else:
            await _spawn_sync(f, ctx, msg, args)


class Plugins:
    def __init__(self, network):
        self.network = network
        self.pluginlist = {"Builtins": Builtins(network)}
        self.ctx = IRCContext(network)
        self.nested = NestedScanner()
        self.spooler = Spooler(self.ctx, chunksize=512, targmax=network.targmax,
            maxmodes=network.maxmodes)

    def load(self, plugin):
        pass

    def unload(self, plugin):
        pass

    def reload(self, plugin):
        pass

    async def dispatch(self, msg):
        self.ctx.set_message(msg)

        with trio.move_on_after(15):
            async with trio.open_nursery() as nursery:
                for name, inst in self.pluginlist.items():
                    nursery.start_soon(self._dispatch, inst, msg)

        for message in self.spooler.spool():
            log.debug(message)
            await utils.send(self.network, message)

        self.ctx.reset_responses()

    async def _dispatch(self, inst, msg):
        try:
            await self._dispatch_event(inst, msg)
        except Exception as e:
            err = commands.msg(self.ctx.to(msg), f"Error: {str(e)}")
            await utils.send(self.network, err)

    async def _dispatch_event(self, inst, msg):
        msgtype = msg.type
        text = msg.text
        dispatched = False
        methods = {name: method for name, method in inspect.getmembers(inst, inspect.ismethod)}

        if msgtype is MsgType.REGULAR and text.startswith(BOTCMD_PREFIX):
            nested_pfx = BOTCMD_PREFIX * 2
            if text.startswith(nested_pfx):
                dispatched = await self._execute_nested(methods, msg, text[len(nested_pfx):])
            else:
                dispatched = await self._execute_command(methods, msg, text[len(BOTCMD_PREFIX):])

        if msgtype is MsgType.CTCP:
            method = "_on_ctcp"
        elif msgtype is MsgType.CTCPREPLY:
            method = f"_on_ctcpreply"
        elif msgtype is MsgType.ACTION:
            method = f"_on_action"
        else:
            method = f"_on_{msg.command.lower()}"

        dispatched = any([
            dispatched,
            await _spawn(self.ctx, methods, msg, method, text)
        ])

        if not dispatched:
            await _spawn(self.ctx, methods, msg, "_uncatched", text)

        await _spawn(self.ctx, methods, msg, "_catchall", text)

    async def _execute_command(self, methods, msg, text):
        cmd = text.split(" ", 1)

        if len(cmd) > 1:
            cmd, args = cmd
        else:
            (cmd,), args = cmd, ''

        cmd = validate_command(cmd)
        if cmd is False:
            return False

        return await _spawn(self.ctx, methods, msg, cmd.lower(), args)

    async def _execute_nested(self, methods, msg, text):
        try:
            cmds = self.nested.scan(text)
        except ValueError as e:
            self.ctx.msg(self.ctx.to(msg), f"Error: {str(e)}")
        else:
            ret =  await self._evaluate(methods, msg, cmds)
            return True if ret else False

    def _expand(self, cmds):
        longest = max((len(cmd) if isinstance(cmd, list) else 1) for cmd in cmds)
        out = [[] for _ in range(longest)]

        for cmd in cmds:
            if isinstance(cmd, list):
                for idx, token in enumerate(cmd):
                    out[idx].append(token)
            else:
                for idx in range(longest):
                    out[idx].append(cmd)

        return out

    async def _evaluate(self, methods, msg, cmds):
        for idx, cmd in enumerate(cmds):
            if isinstance(cmd, list):
                cmds[idx] = await self._evaluate(methods, msg, cmd)
                self.ctx.reset_responses()

        for cmd in self._expand(cmds):
            await self._execute_command(methods, msg, "".join(cmd))

        return [msg.text for msg in self.ctx.responses if msg.text]
