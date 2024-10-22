import sys
import socket
from functools import wraps

from twisted.internet import tcp


class ReusePort(tcp.Port):
    """
    Besides everything tcp.Port does, this sets SO_REUSEPORT on the
    socket created by createInternetSocket (SO_REUSEADDR is already
    set by Twisted).
    """
    def createInternetSocket(self, *args, **kw):
        skt = tcp.Port.createInternetSocket(self, *args, **kw)
        # REUSE_ADDR already set by twisted
        if tcp.platformType == "posix" and sys.platform != "cygwin":
            skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        return skt


class ReuseClient(tcp.Client):
    """
    Besides everything tcp.Client does, this sets SO_REUSEADDR and
    SO_REUSEPORT on the socket created by createInternetSocket
    """
    def createInternetSocket(self, *args, **kw):
        skt = tcp.Client.createInternetSocket(self, *args, **kw)
        # copied platform logic from Port, but Twisted issue 9101
        # comments say REUSEADDR along on Windows is similar-enough to
        # both on Linux (?)
        if tcp.platformType == "posix" and sys.platform != "cygwin":
            skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        return skt


class ReuseConnector(tcp.Connector):
    """
    Allows us to create a ReuseClient instead of a normal Client
    """
    def _makeTransport(self):
        return ReuseClient(self.host, self.port, self.bindAddress, self, self.reactor)


def _wrap_reactor(reactor):

    @wraps(reactor.listenTCP)
    def _listenTCP(port, factory, backlog=50, interface=""):
        p = ReusePort(port, factory, backlog, interface, reactor)
        p.startListening()
        return p
    reactor.listenTCP = _listenTCP

    @wraps(reactor.connectTCP)
    def _connectTCP(host, port, factory, timeout=30, bindAddress=None):
        c = ReuseConnector(host, port, factory, timeout, bindAddress, reactor)
        c.connect()
        return c
    reactor.connectTCP = _connectTCP

    return reactor
