import socket
import threading
import functools
import logging
from urllib3 import HTTPConnectionPool, exceptions, HTTPResponse
from urllib3.util.url import parse_url

try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

from newrelic_telemetry_sdk.client import (
    Client,
    SpanClient,
    MetricClient,
    EventClient,
    LogClient,
)
import pytest


HTTPS_PROXY_UNSUPPORTED_MSG = "Contacting https destinations through https proxies is not supported."
PROXY_ENV_IGNORED_MSG = "Ignoring environment proxy settings as a proxy was found in connection kwargs."


class HttpProxy(threading.Thread):
    def __init__(proxy):
        super(HttpProxy, proxy).__init__()
        proxy.port = proxy.get_open_port()
        proxy.host = "127.0.0.1"
        proxy.connect_host = None
        proxy.connect_port = None
        proxy.headers = None

        class ProxyHandler(BaseHTTPRequestHandler):
            POOL_CLS = Client.POOL_CLS
            server_version = "PROXINATOR/9000"
            protocol_version = "HTTP/1.1"

            def do_CONNECT(self):
                host_port = self.requestline.split(" ", 2)[1]
                proxy.connect_host, proxy.connect_port = host_port.split(":", 1)
                proxy.headers = dict((k.lower(), v) for k, v in self.headers.items())

                self.send_response(200)
                self.end_headers()
                self.close_connection = True

            @staticmethod
            def log_message(*args, **kwargs):
                pass

        proxy.httpd = HTTPServer((proxy.host, proxy.port), ProxyHandler)

    @staticmethod
    def get_open_port():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("", 0))
        port = s.getsockname()[1]
        s.close()
        return port

    def run(self):
        self.httpd.serve_forever()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc, value, tb):
        # Shutdowns the httpd server.
        self.httpd.shutdown()

        # Close the socket so we can reuse it.
        self.httpd.socket.close()

        self.join()


def force_response(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        # Make the actual call to urlopen so urllib3 will attempt a connect.
        # Since the proxy does not actually open a socket to the remote host we
        # expect cPython to raise a ProxyError or ProtocolError and PyPy will
        # raise an OSError or SSLError. For testing these errors can be ignored,
        # we just care that the connect occured with the proper request line.
        try:
            fn(*args, **kwargs)
        except (
            exceptions.ProxyError,
            exceptions.ProtocolError,
            exceptions.SSLError,
            OSError,
        ):
            pass

        response = HTTPResponse(status=202)
        return response

    return wrapper


URLOPEN = force_response(HTTPConnectionPool.urlopen)


@pytest.fixture(scope="module")
def http_proxy():
    proxy = HttpProxy()
    with proxy as p:
        yield p


@pytest.mark.parametrize("client_class", (SpanClient, MetricClient, EventClient, LogClient))
def test_http_proxy_connection_from_env(client_class, http_proxy, monkeypatch, caplog):
    proxy_url = "hTtP://{}:{}".format(http_proxy.host, http_proxy.port)

    monkeypatch.setattr(HTTPConnectionPool, "urlopen", URLOPEN)
    monkeypatch.setenv("https_proxy", proxy_url)

    with caplog.at_level(logging.INFO):
        client = client_class("test-key", "test-host")

    log_record = caplog.records[-1]
    assert log_record.msg == "Using proxy host={0!r} port={1!r}".format(http_proxy.host, http_proxy.port)
    assert str(client._pool.proxy) == proxy_url.lower()

    client.send({})
    assert http_proxy.connect_host == "test-host"
    assert http_proxy.connect_port == "443"
    assert "proxy-authorization" not in http_proxy.headers


@pytest.mark.parametrize("client_class", (SpanClient, MetricClient, EventClient, LogClient))
def test_http_proxy_connection_from_env_with_auth(client_class, http_proxy, monkeypatch, caplog):
    proxy_url_with_auth = "http://username:password@{}:{}".format(http_proxy.host, http_proxy.port)

    monkeypatch.setattr(HTTPConnectionPool, "urlopen", URLOPEN)
    monkeypatch.setenv("https_proxy", proxy_url_with_auth)

    with caplog.at_level(logging.INFO):
        client = client_class("test-key", "test-host")
    log_record = caplog.records[-1]
    assert log_record.msg == "Using proxy host={0!r} port={1!r}".format(http_proxy.host, http_proxy.port)
    assert str(client._pool.proxy) == proxy_url_with_auth.lower()

    client.send({})
    assert http_proxy.connect_host == "test-host"
    assert http_proxy.connect_port == "443"
    assert "proxy-authorization" in http_proxy.headers

    # dXNlcm5hbWU6cGFzc3dvcmQ= is "username:password" base64 encoded
    assert http_proxy.headers["proxy-authorization"] == "Basic dXNlcm5hbWU6cGFzc3dvcmQ="


@pytest.mark.parametrize("client_class", (SpanClient, MetricClient, EventClient, LogClient))
def test_http_proxy_connection_from_kwargs(client_class, http_proxy, monkeypatch):
    proxy_url = "hTtP://{}:{}".format(http_proxy.host, http_proxy.port)

    monkeypatch.setattr(HTTPConnectionPool, "urlopen", URLOPEN)

    client = client_class("test-key", "test-host", _proxy=parse_url(proxy_url))

    assert str(client._pool.proxy) == proxy_url.lower()

    client.send({})
    assert http_proxy.connect_host == "test-host"
    assert http_proxy.connect_port == "443"
    assert "proxy-authorization" not in http_proxy.headers


@pytest.mark.parametrize("client_class", (SpanClient, MetricClient, EventClient, LogClient))
def test_http_proxy_connection_from_kwargs_with_auth_headers(client_class, http_proxy, monkeypatch):
    proxy_url = "http://{}:{}".format(http_proxy.host, http_proxy.port)
    # dXNlcm5hbWU6cGFzc3dvcmQ= is "username:password" base64 encoded
    proxy_basic_auth_headers = {"proxy-authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ="}

    monkeypatch.setattr(HTTPConnectionPool, "urlopen", URLOPEN)

    client = client_class(
        "test-key",
        "test-host",
        _proxy=parse_url(proxy_url),
        _proxy_headers=proxy_basic_auth_headers,
    )

    assert str(client._pool.proxy) == proxy_url.lower()

    client.send({})
    assert http_proxy.connect_host == "test-host"
    assert http_proxy.connect_port == "443"
    assert "proxy-authorization" in http_proxy.headers

    # dXNlcm5hbWU6cGFzc3dvcmQ= is "username:password" base64 encoded
    assert http_proxy.headers["proxy-authorization"] == "Basic dXNlcm5hbWU6cGFzc3dvcmQ="


@pytest.mark.parametrize("client_class", (SpanClient, MetricClient, EventClient, LogClient))
def test_http_proxy_connection_from_kwargs_with_auth_url(client_class, http_proxy, monkeypatch):
    proxy_url = "http://username:password@{}:{}".format(http_proxy.host, http_proxy.port)

    monkeypatch.setattr(HTTPConnectionPool, "urlopen", URLOPEN)

    client = client_class(
        "test-key",
        "test-host",
        _proxy=parse_url(proxy_url),
    )

    assert str(client._pool.proxy) == proxy_url.lower()
    assert client._pool.proxy.auth == "username:password"

    client.send({})
    assert http_proxy.connect_host == "test-host"
    assert http_proxy.connect_port == "443"
    assert "proxy-authorization" not in http_proxy.headers


@pytest.mark.parametrize("client_class", (SpanClient, MetricClient, EventClient, LogClient))
def test_http_proxy_connection_conflicting_kwargs_and_env(client_class, http_proxy, monkeypatch, caplog):
    incorrect_proxy_url_with_auth = "http://baduser:badpassword@badhost:1111"
    correct_proxy_url = "http://{}:{}".format(http_proxy.host, http_proxy.port)
    # dXNlcm5hbWU6cGFzc3dvcmQ= is "username:password" base64 encoded
    proxy_basic_auth_headers = {"proxy-authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ="}

    monkeypatch.setattr(HTTPConnectionPool, "urlopen", URLOPEN)
    # Set environment proxy to incorrect proxy information, and ensure it is ignored in favor of explicit kwargs
    monkeypatch.setenv("https_proxy", incorrect_proxy_url_with_auth)

    with caplog.at_level(logging.INFO):
        client = client_class(
            "test-key",
            "test-host",
            _proxy=parse_url(correct_proxy_url),
            _proxy_headers=proxy_basic_auth_headers,
        )

    assert str(client._pool.proxy) == correct_proxy_url.lower()
    log_record = caplog.records[-1]
    assert log_record.msg == PROXY_ENV_IGNORED_MSG

    client.send({})
    assert http_proxy.connect_host == "test-host"
    assert http_proxy.connect_port == "443"
    assert "proxy-authorization" in http_proxy.headers

    # dXNlcm5hbWU6cGFzc3dvcmQ= is "username:password" base64 encoded
    assert http_proxy.headers["proxy-authorization"] == "Basic dXNlcm5hbWU6cGFzc3dvcmQ="


@pytest.mark.parametrize("client_class", (SpanClient, MetricClient, EventClient, LogClient))
def test_https_proxy_no_connection(monkeypatch, client_class, caplog):
    proxy_host = "random"
    proxy_port = 1234
    # Set the proxy scheme to https so it is not used
    monkeypatch.setenv("https_proxy", "hTTPs://%s:%i" % (proxy_host, proxy_port), prepend=False)

    with caplog.at_level(logging.INFO):
        client = client_class("test-key", "test-host")

    log_record = caplog.records[-1]
    assert log_record.msg == HTTPS_PROXY_UNSUPPORTED_MSG
    assert not client._pool.proxy
