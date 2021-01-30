import inspect
import string
import logging

import trio

from ..core.irclib.context import IRCContext
from ..core.enums import MsgType
from ..core.mixins import IRCMsg, Nick
from ..core import utils
from .builtins import Builtins
from .nested import NestedScanner

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

    def load(self, plugin):
        pass

    def unload(self, plugin):
        pass

    def reload(self, plugin):
        pass

    async def dispatch(self, msg):
        self.ctx.set_message(msg)

        for name, inst in self.pluginlist.items():
            await self._dispatch_event(inst, msg)
            await self.spool(self.ctx.responses)
            self.ctx.reset_responses()

    async def spool(self, responses):
        for response in responses:
            log.debug(response)
            await utils.send(self.network, response)

    async def _dispatch_event(self, inst, msg):
        msgtype = msg.type
        text = msg.text
        # dispatched = False
        methods = {name: method for name, method in inspect.getmembers(inst, inspect.ismethod)}

        if msgtype is MsgType.REGULAR and text.startswith(BOTCMD_PREFIX):
            nested_pfx = BOTCMD_PREFIX * 2
            if text.startswith(nested_pfx):
                await self._execute_nested(methods, msg, text[len(nested_pfx):])
            else:
                await self._execute_command(methods, msg, text[len(BOTCMD_PREFIX):])

        if msgtype is MsgType.CTCP:
            method = "_on_ctcp"
        elif msgtype is MsgType.CTCPREPLY:
            method = f"_on_ctcpreply"
        elif msgtype is MsgType.ACTION:
            method = f"_on_action"
        else:
            method = f"_on_{msg.command.lower()}"

        await _spawn(self.ctx, methods, msg, method, text)

        # TODO: check if command has executed
        # if not dispatched:
        #     await _spawn(ctx, methods, msg, "_uncatched", text)

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

        await _spawn(self.ctx, methods, msg, cmd, args)

    async def _execute_nested(self, methods, msg, text):
        try:
            cmds = self.nested.scan(text)
        except ValueError as e:
            self.ctx.msg(self.ctx.to(msg), f"Error: {str(e)}")
        else:
            responses = []
            print("evaluating", cmds)
            await self._evaluate(methods, msg, cmds, responses)
            print("responses", responses)

    async def _evaluate(self, methods, msg, cmds, responses):
        for idx, cmd in enumerate(cmds):
            if isinstance(cmd, list):
                print(f"  for {cmds}")
                ret = await self._evaluate(methods, msg, cmd, responses)
                cmds[idx] = ret
                self.ctx.reset_responses()

        print("executing", cmds)
        for cmd in cmds:
            print(f"  spawning {cmd}")
            await self._execute_command(methods, msg, cmd)
            ret = [(msg.text if hasattr(msg, "text") else msg) for msg in self.ctx.responses]
            return ret
