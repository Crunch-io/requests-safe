"""
Provide a SafeHTTPAdapter for the requests library that can be used to no
longer allow requests to unsafe networks such as RFC1918/Link-Local and other
such address space.

This is useful for allowing a user provided URL to be provided and then safely
fetched server side without potentially leaking internal documents/secrets.
"""

import ipaddress
import socket
import sys
from socket import error as SocketError
from socket import timeout as SocketTimeout

from requests.adapters import HTTPAdapter
from requests.exceptions import Timeout
from requests.sessions import Session
from urllib3.connection import HTTPConnection, VerifiedHTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from urllib3.exceptions import ConnectTimeoutError, NewConnectionError
from urllib3.poolmanager import PoolManager
from urllib3.util import parse_url

PY2 = sys.version_info[0] == 2

UNSAFE_NETWORKS = [
    # IPv4 unsafe networks
    # RFC1918 (private network)
    ipaddress.ip_network(u"10.0.0.0/8"),
    ipaddress.ip_network(u"172.16.0.0/12"),
    ipaddress.ip_network(u"192.168.0.0/16"),
    # Link-Local
    ipaddress.ip_network(u"169.254.0.0/16"),
    # CG-NAT address space
    ipaddress.ip_network(u"100.64.0.0/10"),
    # Localhost/loopback
    ipaddress.ip_network(u"127.0.0.0/8"),
    # Any IP in Linux
    ipaddress.ip_network(u"0.0.0.0/32"),
    # IETF Protocol Assignments
    ipaddress.ip_network(u"192.0.0.0/24"),
    # TEST-NET-1
    ipaddress.ip_network(u"192.0.2.0/24"),
    # RESERVED
    ipaddress.ip_network(u"192.88.99.0/24"),
    # Benchmark testing
    ipaddress.ip_network(u"198.18.0.0/15"),
    # TEST-NET-2
    ipaddress.ip_network(u"198.51.100.0/24"),
    # TEST-NET-3
    ipaddress.ip_network(u"203.0.113.0/24"),
    # IP Multicast
    ipaddress.ip_network(u"224.0.0.0/4"),
    # RESERVED
    ipaddress.ip_network(u"240.0.0.0/4"),
    # Limited broadcast
    ipaddress.ip_network(u"255.255.255.255/32"),
    # IPv6 unsafe networks
    # Localhost/unspecified address
    ipaddress.ip_network(u"::/128"),
    # Loopback
    ipaddress.ip_network(u"::1/128"),
    # IPv4 mapped address
    ipaddress.ip_network(u"::ffff:0:0/96"),
    # IPv4 translated addresses
    ipaddress.ip_network(u"::ffff:0:0:0/96"),
    # IPv4/IPv6 translation
    ipaddress.ip_network(u"64:ff9b::/96"),
    # Discard prefix
    ipaddress.ip_network(u"100::/64"),
    # Teredo tunneling
    ipaddress.ip_network(u"2001::/32"),
    # Orchid v2 (abondoned)
    ipaddress.ip_network(u"2001:20::/28"),
    # Documentation
    ipaddress.ip_network(u"2001:db8::/32"),
    # 6to4 addressing scheme (deprecated)
    ipaddress.ip_network(u"2002::/16"),
    # ULA address space
    ipaddress.ip_network(u"fc00::/7"),
    # Link-local address space
    ipaddress.ip_network(u"fe80::/10"),
    # Global multicast
    ipaddress.ip_network(u"ff00::/8"),
]


def ip_is_safe(ip):
    """
    Loops over all of the defined unsafe networks and checks if the IP address
    we are attempting to connect to is in one of the aforementioned unsafe
    networks.
    """

    if PY2:
        ip = ip.decode()

    ip = ipaddress.ip_address(ip)

    for network in UNSAFE_NETWORKS:
        if ip in network:
            return False

    return True


def create_connection(
    address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, socket_options=None
):
    """
    Creates a new connection to the address (hostname generally), with a
    timeout and socket options provided.

    With one minor twist:

    It won't attempt to connect a socket to an IP address that is located in
    one of the networks defined in UNSAFE_NETWORKS, silently ignoring those IP
    addresses if returned in DNS.
    """

    host, port = address

    if host.startswith("["):  # pragma: nocover
        host = host.strip("[]")
    err = None

    for res in socket.getaddrinfo(
        host,
        port,
        0,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,  # TCP sockets only
        (
            # We provided port number numerically
            socket.AI_NUMERICSERV
            # We don't want v4 or v6 if they are not configured
            | socket.AI_ADDRCONFIG
        ),
    ):
        af, socktype, proto, canonname, sa = res
        sock = None

        # This is the ultra-important check, only allow the connection request
        # through if the IP we are about to connect to is considered safe.

        if not ip_is_safe(sa[0]):
            continue

        try:
            sock = socket.socket(af, socktype, proto)

            # If provided, set socket level options before connecting.

            for opt in socket_options:
                sock.setsockopt(*opt)

            if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)

            sock.connect(sa)

            return sock

        except socket.error as e:
            err = e

            if sock is not None:
                sock.close()
                sock = None

    if err is not None:
        raise err

    raise socket.error("getaddrinfo returns an empty list")


class SafeHTTPConnection(HTTPConnection):
    """
    Use the base class, except for creating a new connection, where we want to
    use our create_connection that verifies the IP we are connecting to is safe
    to connect to.
    """

    def _new_conn(self):
        """
        Override a non-public member which is used to create the connection,
        yes, implementation detail, caveat emptor
        """

        extra_kw = {}

        if self.socket_options:
            extra_kw["socket_options"] = self.socket_options

        try:
            conn = create_connection(
                (self.host.rstrip("."), self.port), self.timeout, **extra_kw
            )

        except SocketTimeout:
            raise ConnectTimeoutError(
                self,
                "Connection to %s timed out. (connect timeout=%s)"
                % (self.host, self.timeout),
            )

        except SocketError as e:
            raise NewConnectionError(
                self, "Failed to establish a new connection: %s" % e
            )

        return conn


class SafeHTTPSConnection(SafeHTTPConnection, VerifiedHTTPSConnection):
    """
    Use our SafeHTTPConnection with the urllib3 provided
    VerifiedHTTPSConnection. urllib3 allows for switching between two different
    types of HTTPSConnection, but we care about safety so we only ever want to
    use the VerifiedHTTPSConnection
    """

    pass


class SafeHTTPConnectionPool(HTTPConnectionPool):
    """
    Simple override of the ConnectionCls used by HTTPConnectionPool
    """

    ConnectionCls = SafeHTTPConnection


class SafeHTTPSConnectionPool(HTTPSConnectionPool):
    """
    Simple override of the ConnectionCls used by HTTPSConnectionPool
    """

    ConnectionCls = SafeHTTPSConnection


class SafePoolManager(PoolManager):
    """
    A urllib3 PoolManager that overrides the default pool classes with ones
    that know how to verify the IP address to be connected to is considered
    safe
    """

    def __init__(self, *args, **kwargs):
        super(SafePoolManager, self).__init__(*args, **kwargs)

        self.pool_classes_by_scheme = {
            "http": SafeHTTPConnectionPool,
            "https": SafeHTTPSConnectionPool,
        }


class SafeHTTPAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        """
        Initialize the pool manager using the SafePoolManager which will use
        our SafeHTTPConnection/SafeHTTPSConnection instead of the default.
        """

        # save these values for pickling (not really related to the
        # initialization of the pool manager, but copied from
        # requests.adapter.HTTPAdapter)
        self._pool_connections = connections
        self._pool_maxsize = maxsize
        self._pool_block = block

        self.poolmanager = SafePoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            strict=True,
            **pool_kwargs
        )


def apply(session):
    adapter = SafeHTTPAdapter()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
