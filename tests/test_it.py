import json
import socket

import pytest
import requests
from mocket import Mocket
from mocket.mockhttp import Entry

import requests_safe

example_com_ips = {"2606:2800:220:1:248:1893:25c8:1946", "93.184.216.34"}


def strify_ips(lst):
    return "getaddrinfo-ips: " + ", ".join([ip for (family, ip, port) in lst])


# These are considered safe and connections should be allowed without issues.
safe_ips = [
    [
        # example.com AAAA record (considered safe)
        (socket.AF_INET6, "2606:2800:220:1:248:1893:25c8:1946", 80)
    ],
    [
        # example.com A record (considered safe)
        (socket.AF_INET, "93.184.216.34", 80)
    ],
]

# The first ip address in the mix here is disallowed, but connections should still succeed
mixed_ips = [
    [
        # IP address in documentation range, disallowed
        (socket.AF_INET6, "2001:db8::1", 80),
        # example.com AAAA record (considered safe)
        (socket.AF_INET6, "2606:2800:220:1:248:1893:25c8:1946", 80),
    ],
    [
        # IP address in documentation range, disallowed
        (socket.AF_INET6, "2001:db8::1", 80),
        # example.com A record (considered safe)
        (socket.AF_INET, "93.184.216.34", 80),
    ],
    [
        # IP address in RFC1918 range, disallowed
        (socket.AF_INET, "10.10.10.58", 80),
        # example.com A record (considered safe)
        (socket.AF_INET, "93.184.216.34", 80),
    ],
]

unsafe_ips = [
    [
        # IP address in documentation range, disallowed
        (socket.AF_INET6, "2001:db8::1", 80)
    ],
    [
        # IP address in RFC1918 range, disallowed
        (socket.AF_INET, "10.10.10.58", 80)
    ],
]


def test_apply():
    s = requests.Session()

    requests_safe.apply(s)

    assert isinstance(s.adapters["http://"], requests_safe.SafeHTTPAdapter)
    assert isinstance(s.adapters["https://"], requests_safe.SafeHTTPAdapter)

    s.close()


@pytest.fixture(params=safe_ips + mixed_ips, ids=strify_ips)
def request_succeeds(request, fake_getaddrinfo):
    for (family, ip, port) in request.param:
        fake_getaddrinfo.append(
            (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, port))
        )

        # Set up a fake entry to return some data for all of the IP's so mocket
        # doesn't try to connect if it can't find an entry.
        mocket_entry = Entry(
            "http://example.com/info.json",
            Entry.GET,
            Entry.response_cls(body=json.dumps({"ip": ip}), status=200, headers=None),
        )

        mocket_entry.location = (ip, port)
        Mocket.register(mocket_entry)


@pytest.fixture(params=unsafe_ips, ids=strify_ips)
def request_fails(request, fake_getaddrinfo):
    for (family, ip, port) in request.param:
        fake_getaddrinfo.append(
            (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, port))
        )


@pytest.fixture
def apply_safety_net(fake_getaddrinfo):
    fake_getaddrinfo.append(
        (
            socket.AF_INET6,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("2606:2800:220:1:248:1893:25c8:1946", 80),
        )
    )

    # Set up a fake entry to return some data for all of the IP's so mocket
    # doesn't try to connect if it can't find an entry.
    mocket_entry = Entry(
        "http://example.com/info.json",
        Entry.GET,
        Entry.response_cls(
            body=json.dumps({"ip": "2606:2800:220:1:248:1893:25c8:1946"}),
            status=200,
            headers=None,
        ),
    )

    mocket_entry.location = ("2606:2800:220:1:248:1893:25c8:1946", 80)
    Mocket.register(mocket_entry)


def test_safe_requests(session, request_succeeds):
    ret = session.get("http://example.com/info.json")

    # This will validate that we connected to a safe ip, even if the list may
    # have contained unsafe IPs
    assert ret.json()["ip"] in example_com_ips


def test_unsafe_requests_fails(session, request_fails):
    with pytest.raises(requests.exceptions.ConnectionError) as exc:
        session.get("http://exampe.com/info.json")

    assert "getaddrinfo returns an empty list" in str(exc.value)


def test_safe_requests_ip(session, apply_safety_net):
    # Verify bare IPv6 URL works
    ret = session.get("http://[2606:2800:220:1:248:1893:25c8:1946]/info.json")

    # This will validate that we connected to a safe ip, even if the list may
    # have contained unsafe IPs
    assert ret.json()["ip"] in example_com_ips


def test_redirect_to_ip_unsafe_fails(session, fake_getaddrinfo):
    fake_getaddrinfo.append(
        (
            socket.AF_INET6,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("2606:2800:220:1:248:1893:25c8:1946", 80),
        )
    )

    # Set up a fake entry to return some data for all of the IP's so mocket
    # doesn't try to connect if it can't find an entry.
    mocket_entry = Entry(
        "http://example.com/info.json",
        Entry.GET,
        Entry.response_cls(
            body=json.dumps({"ip": "2606:2800:220:1:248:1893:25c8:1946"}),
            status=301,
            headers={"Location": "http://10.10.10.58/other.json"},
        ),
    )

    mocket_entry.location = ("2606:2800:220:1:248:1893:25c8:1946", 80)
    Mocket.register(mocket_entry)

    mocket_entry = Entry(
        "http://10.10.10.58/other.json",
        Entry.GET,
        Entry.response_cls(
            body=json.dumps({"ip": "10.10.10.58"}), status=200, headers=None
        ),
    )

    mocket_entry.location = ("10.10.10.58", 80)
    Mocket.register(mocket_entry)

    with pytest.raises(requests.exceptions.ConnectionError) as exc:
        session.get("http://exampe.com/info.json")

    assert "getaddrinfo returns an empty list" in str(exc.value)


def test_socket_raises(session, apply_safety_net, fake_socket_raises):
    with pytest.raises(requests.exceptions.ConnectionError):
        session.get("http://example.com/info.json")


def test_socket_timeout(session, apply_safety_net, fake_socket_timeout):
    with pytest.raises(requests.exceptions.ConnectTimeout):
        session.get("http://example.com/info.json")
