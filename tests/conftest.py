import json
import socket

import mocket
import pytest
import requests
from mocket.mockhttp import Entry

import requests_safe


@pytest.fixture
def disable_socket():
    with mocket.Mocketizer():
        yield


@pytest.fixture
def fake_getaddrinfo(monkeypatch, disable_socket):
    results = []

    def _getaddrinfo(host, port, family=None, socktype=None, proto=None, flags=None):
        if host == "10.10.10.58":
            return

        for entry in results:
            yield entry

    monkeypatch.setattr(socket, "getaddrinfo", _getaddrinfo)

    yield results


@pytest.fixture
def fake_socket_raises(monkeypatch, disable_socket):
    class _socket(object):
        def __init__(self, family, socktype, proto):
            pass

        def setsockopt(self, *opts):
            pass

        def settimeout(self, timeout):
            pass

        def close(self):
            pass

        def connect(self, addr):
            raise socket.error("Always fails")

    monkeypatch.setattr(socket, "socket", _socket)


@pytest.fixture
def fake_socket_timeout(monkeypatch, disable_socket):
    def _socket(family, socktype, proto):
        raise socket.timeout("This always fails")

    monkeypatch.setattr(socket, "socket", _socket)


@pytest.fixture
def session():
    with requests.Session() as s:
        requests_safe.apply(s)

        yield s
