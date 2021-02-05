from ..core import utils
from ..core.enums import MsgType
from ..core.irclib import commands
from ..core.utils.dpaste_org import PasteBin
from ..core.utils.utf8utils import UTF8Chunker
from ..core.utils.environment import Env

import logging

INSTANT_THRESHOLD = 7
MORE_THRESHOLD = 7
MAX_MORES = MORE_THRESHOLD - INSTANT_THRESHOLD
log = logging.getLogger("mjollnir")


def pastebin(messages):
    return PasteBin().paste("\n".join(m.text for m in messages))


def filter_chars(text):
    if text.startswith("\x01"):
        text = text[1:]

    return "".join(c for c in text if c not in "\x00\r")


def _maxlinelen(msg, chunksize):
    unavailable = len(f":{msg.sender} {msg.command} {msg.recipient} \r\n")
    # TODO
    # if msg.args[-1].startswith(":"):
    unavailable += 1

    return chunksize - unavailable


class Spooler:
    def __init__(self, ctx, *, chunksize, targmax, maxmodes):
        self.ctx = ctx
        self.chunksize = chunksize
        self.current_chunksize = chunksize
        self.targmax = targmax
        self.maxmodes = maxmodes
        self.chunker = UTF8Chunker()
        self.reset()

    def spool(self):
        self.current_chunksize = self.chunksize

        for response in self.ctx.responses:
            self._process(response)
            if self.count > INSTANT_THRESHOLD:
                break

        if self.count > INSTANT_THRESHOLD:
            self.chunked = []
            self._populate_mores()

            suffix = utils.morefmt(len(self.mores)).encode()
            self.chunked[-1] += suffix

        if len(self.mores) > MAX_MORES:
            self.chunked = []
            self.mores = []
            self._paste()

        if self.mores:
            msg = self.ctx.incoming
            recipient = self.ctx.to(msg)
            Env().mores[recipient][msg.identhost] = self.mores[::-1]

        for chunk in self.chunked:
            yield chunk

        self.reset()

    def reset(self):
        self.chunked = []
        self.mores = []

    def _process(self, msg):
        if msg.type in (MsgType.REGULAR, MsgType.NOTICE):
            self._process_textmessage(msg)
        elif msg.command in self.targmax:
            log.debug(f"spooler.feed {msg.command} is subject to TARGMAX")
            self.chunked.append(msg)
        elif msg.command == "MODE" and self.maxmodes > -1:
            log.debug(f"spooler.feed {msg.command} is subject to MAXMODES")
            self.chunked.append(msg)
        else:
            self.chunked.append(msg)

    def _process_textmessage(self, msg):
        for count, chunk in enumerate(self._chunkify(msg), 1):
            self.chunked.append(chunk)
            if count > INSTANT_THRESHOLD:
                break

    def _populate_mores(self):
        bailout = False
        total = 1
        for response in self.ctx.responses:
            for chunk in self._chunkify(response):
                if total <= INSTANT_THRESHOLD:
                    self.chunked.append(chunk)
                else:
                    self.mores.append(chunk)

                # Checking total greater than threshold before incrementing
                # appends one extra message, which is used later to know
                # if we should go the pastebin route
                if total > MORE_THRESHOLD:
                    bailout = True
                    break

                total += 1
                if total == INSTANT_THRESHOLD:
                    suffix_len = len(utils.morefmt(MAX_MORES).encode())
                    self.current_chunksize = self.chunksize - suffix_len

            if bailout:
                break

    def _paste(self):
        msg = self.ctx.incoming
        responses = self.ctx.responses
        pasteurl = pastebin(responses)
        length = sum(len(response.text.split("\n")) for response in responses)
        plur = "s" if length != 1 else ""
        s = f"{msg.nick}: look at {pasteurl} ({length} line{plur} long)"
        self.chunked.append(commands.msg(self.ctx.to(msg), s))

    def _chunkify(self, msg):
        text = filter_chars(msg.text)

        for line in text.split("\n"):
            self.chunker.set_stream(line)
            while not self.chunker.finished:
                chunksize = _maxlinelen(msg, self.current_chunksize)
                chunk = self.chunker.next_chunk(chunksize)
                if chunk is None:
                    break

                newmsg = msg.copy()
                newmsg.encoded = True
                newmsg.text = chunk
                yield newmsg

    @property
    def count(self):
        return len(self.chunked)