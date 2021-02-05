import logging
from random import random, choice, randint

import trio

from ..core import utils
from ..core.utils import utf8utils
from ..core.utils.environment import Env

log = logging.getLogger("mjollnir")


def advratto(size):
    if size is None:
        mult = 1
    elif "giga" in size or "iper" in size:
        mult = 4 if random() > 1/9 else 8
    elif "mega" in size or "maxi" in size:
        mult = 3
    elif "super" in size:
        mult = 2
    else:
        mult = 1

    fmt = "8={}==D"
    mast = choice(["==", "===", "====", "======", "=================="])
    ratto = fmt.format(mast*mult)
    if random() < 1/7:
        ratto += "O:"

    return ratto


class Builtins:
    def __init__(self, network):
        self.network = network
        self.idle_requested = {}

    def cap(self, irc, msg, text):
        irc.reply("com!")

    def echo(self, irc, msg, text):
        irc.reply(text)

    def act(self, irc, msg, text):
        irc.reply_action(text)

    def reverse(self, irc, msg, text):
        irc.reply(text[::-1])

    def unireverse(self, irc, msg, text):
        unisplit = utf8utils.split(text)
        irc.reply("".join(reversed(unisplit)))

    def len(self, irc, msg, text):
        irc.reply(len(text))

    def unilen(self, irc, msg, text):
        irc.reply(len(utf8utils.split(text)))

    def ratto(self, irc, msg, text):
        irc.reply(advratto(text))

    def more(self, irc, msg, text):
        Env().cleanup()
        recipient = irc.to(msg)
        mores = Env().mores[recipient][msg.identhost]
        if mores is not None:
            mores_cnt = len(mores)
            if mores_cnt > 0:
                more = mores.pop()
                text = more.text.decode()
                cnt = mores_cnt - 1
                if cnt > 0:
                    text += utils.morefmt(cnt)

                irc.reply(text)
            else:
                irc.reply("No more messages.")


    def isin(self, irc, msg, nick):
        if not irc.in_channel() or not nick:
            return

        channel = self.network.channels[msg.recipient]
        me = self.network.identity["nick"]
        if irc.nick_cmp(me, nick):
            irc.reply("dah, I'm here ...")
        elif irc.nick_isin(nick, channel):
            irc.reply(f"{nick} is right there")
            irc.reply_action(f"points at {nick}")
        else:
            irc.reply(f"I can't see {nick} in {channel}.")

    def idle(self, irc, msg, text):
        if text:
            nick = irc.nick_tolower(text)
            self.idle_requested[nick] = (irc.to(msg), utils.timestamp_now())
            irc.raw("WHOIS", [nick, nick])

    def dump(self, irc, msg, text):
        caps = ", ".join(f'{k}={v}' for k, v in self.network.capabilities.items())
        irc.reply(f"{self.network.name}: {self.network.identity['nick']}!{self.network.identity['ident']}@{self.network.hostname} +{''.join(self.network.ownmodes)} MAXMODES:{self.network.maxmodes} {self.network.targmax}")
        irc.reply(caps)
        if irc.in_channel():
            channel = self.network.channels[msg.recipient]
            modes = f"+{''.join(channel.modes.keys())}"
            args = f"{' '.join(val for val in channel.modes.values() if val)}"
            irc.reply(f"{channel}: users: {len(channel.nicks)}, modes: {modes} {args}")
            if channel.topic["text"]:
                irc.reply(f"setby:{channel.topic['setby']}, timestamp:{channel.topic['timestamp']}, topic:'{channel.topic['text']}'")

    def _on_ctcp(self, irc, msg, text):
        reply = None
        ctcp = msg.ctcpname
        if ctcp == "PING":
            reply = text
        elif ctcp == "VERSION":
            reply = "Mjollnir \\o/"
        elif ctcp == "DCC":
            reply = "Mjollnir doesn't support DCCs... yet!"
        elif ctcp == "SOURCE":
            reply = "https://github.com/EdmundOgban/Mjollnir"

        if reply:
            irc.ctcpreply(ctcp, reply)

    def _purge_idle(self):
        self.idle_requested = {k: v for k, v in self.idle_requested.items()
            if utils.timestamp_now() < v[1] + 30}

    def _got_answer(self, msg, fmt, tolower):
        ret = None
        target = tolower(msg.args[1])

        self._purge_idle()
        v = self.idle_requested.get(target)
        if v:
            recipient, _ = v
            ret = (recipient, fmt.format(target=msg.args[1], secs=msg.args[2],
                network=self.network.name))
            self.idle_requested.pop(target)

        return ret

    def _on_317(self, irc, msg, text):
        fmt = "{target} has been idle {secs} seconds"
        ret = self._got_answer(msg, fmt, irc.nick_tolower)
        if ret:
            irc.msg(*ret)

    def _not_online(self, irc, msg, text):
        fmt = "{target} is not on {network}"
        ret = self._got_answer(msg, fmt, irc.nick_tolower)
        if ret:
            irc.msg(*ret)

    def _on_401(self, irc, msg, text):
        self._not_online(irc, msg, text)

    def _on_402(self, irc, msg, text):
        self._not_online(irc, msg, text)

# Builtins.calc.tags = dict(threaded=True)
