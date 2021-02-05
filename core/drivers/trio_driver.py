import logging
import random
import string

import trio

from ..exceptions import DriverConnectionError
from ..irclib import parser, commands

log = logging.getLogger("mjollnir")


def _decode(line):
    encodings = ('utf8', 'iso-8859-15')
    for enc in encodings:
        try:
            decoded = line.decode(enc)
        except UnicodeDecodeError:
            pass
        else:
            return decoded


class Driver:
    def __init__(self, identity, rsendq, wsendq):
        self.identity = identity
        self.servers = iter(identity["servers"])
        self.rsendq = rsendq
        self.wsendq = wsendq
        self._conn = None
        self._socket_connected = trio.Event()

    async def connect(self):
        if not self.connected:
            await self._connect()

    async def disconnect(self, reason=""):
        if self.connected:
            await self._send(commands.quit(reason))
            await self._conn.aclose()
            self._socket_connected = trio.Event()
            self._conn = None

    async def perform(self):
        nick = self.identity["nick"]
        await self._send(commands.nick(nick))

    async def receive(self):
        await self._socket_connected.wait()

        s = bytearray()
        while self._conn:
            mesg = await self._conn.receive_some(4096)
            if not mesg:
                raise DriverConnectionError("Connection closed by peer")

            if s:
                mesg = s + mesg
                s = bytearray()

            for m in mesg.split(b'\n'):
                if m.endswith(b'\r'):
                    m = m.strip()
                    if m:
                        decoded = _decode(m)
                        msg = parser.parse(decoded)
                        yield msg
                else:
                    s += m

    async def spool(self):
        await self._socket_connected.wait()

        while True:
            msg = await self.rsendq.receive()
            await self._send(msg)

    async def _connect(self):
        host = None
        port = None
        secure = None

        while not self._conn:
            host, port, secure, verify = next(self.servers)
            log.info(f"trio_driver Trying {host}:{'+' if secure else ''}{port}")
            if secure and not verify:
                log.warning(f"trio_driver Trio does not support skipping certificate validation")

            try:
                if secure:
                    self._conn = await trio.open_ssl_over_tcp_stream(host, port)
                else:
                    self._conn = await trio.open_tcp_stream(host, port)
            except OSError as e:
                raise DriverConnectionError(f"OSError: '{str(e)}'")

            if not self._conn:
                log.info(f"trio_driver Connection refused. Trying next host in 5 seconds...")
                await trio.sleep(5)

        self._socket_connected.set()
        log.info(f"trio_driver Connected to {host}:{'+' if secure else ''}{port}")
        await self._identify()

    async def _identify(self):
        for msg in commands.identify(self.identity):
            await self._send(msg)

    async def _send(self, msg):
        if isinstance(msg, str) or not msg.encoded:
            s = f"{msg}\r\n".encode("utf8")
        elif msg.encoded:
            s = bytes(msg) + b"\r\n"
        else:
            log.warning(f"trio_driver._send Ignoring request to send '{msg}'")
            return

        await self._conn.send_all(s)

    @property
    def connected(self):
        return self._conn is not None
