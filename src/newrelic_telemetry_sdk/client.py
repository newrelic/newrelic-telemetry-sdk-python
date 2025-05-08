# Copyright 2019 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
import uuid
import zlib

import urllib3
from urllib3.util import parse_url

try:
    from urllib.request import getproxies
except ImportError:
    from urllib import getproxies


_logger = logging.getLogger(__name__)

try:
    from newrelic_telemetry_sdk.version import version as __version__
except ImportError:  # pragma: no cover
    __version__ = "unknown"

USER_AGENT = f"NewRelic-Python-TelemetrySDK/{__version__}"

__all__ = ("EventClient", "HTTPError", "HTTPResponse", "HTTPSConnectionPool", "LogClient", "MetricClient", "SpanClient")


class HTTPError(ValueError):
    """Unexpected HTTP Status"""


class HTTPResponse(urllib3.HTTPResponse):
    """A wrapper for urllib3.HTTPResponse, providing additional helper methods"""

    def __init__(self, response):
        """Initialize the wrapper with an urllib3.HTTPResponse object"""
        self._response = response

    def __getattr__(self, name):
        """Expose attributes and methods of the original urllib3.HTTPResponse object"""
        return getattr(self._response, name)

    def json(self):
        """Returns the json-encoded content of a response.

        :rtype: dict
        """
        return json.loads(self.data.decode("utf-8"))

    @property
    def ok(self):
        """Return true if status code indicates success"""
        return 200 <= self.status < 300  # noqa: PLR2004

    def raise_for_status(self):
        """Raise an exception for an unsuccessful HTTP status code

        :raises HTTPError: if response status is not successful
        """
        if not self.ok:
            raise HTTPError(self.status, self)


# No longer a subclass, kept for backwards compatibility
HTTPSConnectionPool = urllib3.HTTPSConnectionPool


class Client:
    """HTTP Client for interacting with New Relic APIs

    This class is used to send data to the New Relic APIs over HTTP. This class
    will automatically handle retries as needed.

    :param license_key: New Relic license key
    :type license_key: str
    :param host: (optional) Override the host for the client.
    :type host: str
    :param port: (optional) Override the port for the client. Default: 443
    :type port: int
    :param \\**connection_pool_kwargs: Configuration options for urllib3.HTTPSConnectionPool.
        See https://urllib3.readthedocs.io/en/stable/reference/urllib3.connectionpool.html#urllib3.HTTPSConnectionPool

    Usage::

        >>> import os
        >>> license_key = os.environ.get("NEW_RELIC_LICENSE_KEY", "")
        >>> client = Client(license_key, host="metric-api.newrelic.com")
        >>> response = client.send({})
        >>> client.close()
    """

    POOL_CLS = HTTPSConnectionPool
    PAYLOAD_TYPE = ""
    HOST = ""
    PATH = "/"
    HEADERS = urllib3.make_headers(keep_alive=True, accept_encoding=True, user_agent=USER_AGENT)

    def __init__(self, license_key, host=None, port=443, **connection_pool_kwargs):
        if not license_key:
            msg = f"Invalid license key: {license_key}"
            raise ValueError(msg)

        host = host or self.HOST
        headers = self.HEADERS.copy()
        headers.update({"Api-Key": license_key, "Content-Encoding": "gzip", "Content-Type": "application/json"})
        retries = urllib3.Retry(total=False, connect=None, read=None, redirect=0, status=None)

        proxy, proxy_headers = self._parse_proxy_settings(connection_pool_kwargs)

        # Merge custom config into default config
        merged_connection_pool_kwargs = {
            "host": host,
            "port": port,
            "retries": retries,
            "_proxy": proxy,
            "_proxy_headers": proxy_headers,
        }
        merged_connection_pool_kwargs.update(connection_pool_kwargs)

        # Merge custom headers with default headers
        if "headers" in connection_pool_kwargs:
            # If the user has specified headers, we need to copy the existing
            # headers so we don't lose any of the default ones.
            headers.update(connection_pool_kwargs["headers"])

        merged_connection_pool_kwargs["headers"] = headers

        self._pool = self.POOL_CLS(**merged_connection_pool_kwargs)
        self._headers = self._pool.headers

    def _parse_proxy_settings(self, connection_pool_kwargs=None):
        """
        Check environment to see if https traffic should be proxied
        and return the proxy information to pass to the connectionpool.
        """

        proxies = getproxies()
        proxy = proxies.get("https", None)
        proxy_headers = None
        if proxy and connection_pool_kwargs and "_proxy" in connection_pool_kwargs:
            _logger.warning("Ignoring environment proxy settings as a proxy was found in connection kwargs.")
        elif proxy:
            proxy = parse_url(proxy)
            _logger.info("Using proxy host=%r port=%r", proxy.host, proxy.port)
            if proxy.scheme.lower() != "http":
                _logger.warning("Contacting https destinations through %s proxies is not supported.", proxy.scheme)
                proxy = None
            elif proxy.auth:
                # https://tools.ietf.org/html/rfc7617
                #
                # The username/password encoding is not specified by a standard.
                # "this specification continues to leave the default encoding undefined"
                #
                # parse_url will encode non-ascii characters into a
                # percent-encoded string. As a result, we make the assumption
                # that anything returned from parse_url is utf-8 encoded.
                #
                # This is, of course, not guaranteed to be interpreted
                # correctly by the proxy server, but the failure mode will
                # hopefully be interpreted as an incorrect username/password
                # combination rather than causing a security issue where
                # information may be leaked (control characters, etc.)
                proxy_headers = urllib3.make_headers(proxy_basic_auth=proxy.auth)

        return proxy, proxy_headers

    def add_version_info(self, product, product_version):
        """Adds product and version information to a User-Agent header

        This method implements
        https://tools.ietf.org/html/rfc7231#section-5.5.3

        :param product: The product name using the SDK
        :type product: str
        :param product_version: The version string of the product in use
        :type product_version: str
        """
        product_ua_header = f" {product}/{product_version}"
        self._headers["user-agent"] += product_ua_header

    def close(self):
        """Close all open connections and disable internal connection pool."""
        self._pool.close()

    @staticmethod
    def _compress_payload(payload):
        level = zlib.Z_DEFAULT_COMPRESSION
        compressor = zlib.compressobj(level, zlib.DEFLATED, 31)
        payload = compressor.compress(payload)
        payload += compressor.flush()
        return payload

    def _create_payload(self, items, common):
        payload = {self.PAYLOAD_TYPE: items}
        if common:
            payload["common"] = common

        payload = json.dumps([payload], separators=(",", ":"))
        if not isinstance(payload, bytes):
            payload = payload.encode("utf-8")

        return self._compress_payload(payload)

    def send(self, item, timeout=None):
        """Send a single item

        :param item: The object to send
        :type item: dict
        :param timeout: (optional)  a timeout in seconds for sending the request
        :type timeout: int
        :rtype: HTTPResponse
        """
        return self.send_batch((item,), timeout=timeout)

    def send_batch(self, items, common=None, timeout=None):
        """Send a batch of items

        :param items: An iterable of items to send to New Relic.
        :type items: list or tuple
        :param common: (optional) A map of attributes that will be set on each item.
        :type common: dict
        :param timeout: (optional)  a timeout in seconds for sending the request
        :type timeout: int
        :rtype: HTTPResponse
        """
        # Specifying the headers argument overrides any base headers existing
        # in the pool, so we must copy all existing headers
        headers = self._headers.copy()

        # Generate a unique request ID for this request
        headers["x-request-id"] = str(uuid.uuid4())

        payload = self._create_payload(items, common)
        urllib3_response = self._pool.urlopen("POST", self.PATH, body=payload, headers=headers, timeout=timeout)
        if not isinstance(urllib3_response, urllib3.HTTPResponse):
            exc_msg = f"Expected urllib3.HTTPResponse, got {type(urllib3_response)}"
            raise TypeError(exc_msg)

        return HTTPResponse(urllib3_response)


class SpanClient(Client):
    """HTTP Client for interacting with the New Relic Span API

    This class is used to send spans to the New Relic Span API over HTTP.

    :param license_key: New Relic license key
    :type license_key: str
    :param host: (optional) Override the host for the span API endpoint.
    :type host: str
    :param port: (optional) Override the port for the client. Default: 443
    :type port: int

    Usage::

        >>> import os
        >>> license_key = os.environ.get("NEW_RELIC_LICENSE_KEY", "")
        >>> span_client = SpanClient(license_key)
        >>> response = span_client.send({})
        >>> span_client.close()
    """

    HOST = "trace-api.newrelic.com"
    PATH = "/trace/v1"
    PAYLOAD_TYPE = "spans"


class MetricClient(Client):
    """HTTP Client for interacting with the New Relic Metric API

    This class is used to send metrics to the New Relic Metric API over HTTP.

    :param license_key: New Relic license key
    :type license_key: str
    :param host: (optional) Override the host for the metric API endpoint.
    :type host: str
    :param port: (optional) Override the port for the client. Default: 443
    :type port: int

    Usage::

        >>> import os
        >>> license_key = os.environ.get("NEW_RELIC_LICENSE_KEY", "")
        >>> metric_client = MetricClient(license_key)
        >>> response = metric_client.send({})
        >>> metric_client.close()
    """

    HOST = "metric-api.newrelic.com"
    PATH = "/metric/v1"
    PAYLOAD_TYPE = "metrics"


class EventClient(Client):
    """HTTP Client for interacting with the New Relic Event API

    This class is used to send events to the New Relic Event API over HTTP.

    :param license_key: New Relic license key
    :type license_key: str
    :param host: (optional) Override the host for the event API endpoint.
    :type host: str
    :param port: (optional) Override the port for the client. Default: 443
    :type port: int

    Usage::

        >>> import os
        >>> license_key = os.environ.get("NEW_RELIC_LICENSE_KEY", "")
        >>> event_client = EventClient(license_key)
        >>> response = event_client.send({})
        >>> event_client.close()
    """

    HOST = "insights-collector.newrelic.com"
    PATH = "/v1/accounts/events"

    def _create_payload(self, items, common):  # noqa: ARG002
        payload = json.dumps(items)
        if not isinstance(payload, bytes):
            payload = payload.encode("utf-8")

        return self._compress_payload(payload)

    def send_batch(self, items, timeout=None):
        """Send a batch of items

        :param items: An iterable of items to send to New Relic.
        :type items: list or tuple
        :param timeout: (optional)  a timeout in seconds for sending the request
        :type timeout: int

        :rtype: HTTPResponse
        """
        return super().send_batch(items, None, timeout=timeout)


class LogClient(Client):
    """HTTP Client for interacting with the New Relic Log API

    This class is used to send log messages to the New Relic Log API over HTTP.
    :param license_key: New Relic license key
    :type license_key: str
    :param host: (optional) Override the host for the metric API endpoint.
    :type host: str
    :param port: (optional) Override the port for the client. Default: 443
    :type port: int

    Usage::

        >>> import os
        >>> license_key = os.environ.get("NEW_RELIC_LICENSE_KEY", "")
        >>> log_client = LogClient(license_key)
        >>> response = log_client.send({})
        >>> log_client.close()
    """

    HOST = "log-api.newrelic.com"
    PATH = "/log/v1"
    PAYLOAD_TYPE = "logs"
