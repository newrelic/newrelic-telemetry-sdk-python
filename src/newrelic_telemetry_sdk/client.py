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

USER_AGENT = "NewRelic-Python-TelemetrySDK/{}".format(__version__)

__all__ = ("SpanClient", "MetricClient", "EventClient", "HTTPError", "HTTPResponse")


class HTTPError(ValueError):
    """Unexpected HTTP Status"""


class HTTPResponse(urllib3.HTTPResponse):
    """Response object with helper methods

    :ivar headers: The HTTP headers
    :ivar status: The HTTP status code
    :ivar data: The raw byte encoded response data
    """

    def json(self):
        """Returns the json-encoded content of a response.

        :rtype: dict
        """
        return json.loads(self.data.decode("utf-8"))

    @property
    def ok(self):
        """Return true if status code indicates success"""
        return 200 <= self.status < 300

    def raise_for_status(self):
        """Raise an exception for an unsuccessful HTTP status code

        :raises HTTPError: if response status is not successful
        """
        if not self.ok:
            raise HTTPError(self.status, self)


class HTTPSConnectionPool(urllib3.HTTPSConnectionPool):
    """Connection pool providing HTTPResponse objects"""

    ResponseCls = HTTPResponse


class Client(object):
    """HTTP Client for interacting with New Relic APIs

    This class is used to send data to the New Relic APIs over HTTP. This class
    will automatically handle retries as needed.

    :param insert_key: Insights insert key
    :type insert_key: str
    :param host: (optional) Override the host for the client.
    :type host: str
    :param port: (optional) Override the port for the client.
        Default: 443
    :type port: int

    Usage::

        >>> import os
        >>> insert_key = os.environ.get("NEW_RELIC_INSERT_KEY", "")
        >>> client = Client(insert_key, host="metric-api.newrelic.com")
        >>> response = client.send({})
        >>> client.close()
    """

    POOL_CLS = HTTPSConnectionPool
    PAYLOAD_TYPE = ""
    HOST = ""
    PATH = "/"
    HEADERS = urllib3.make_headers(
        keep_alive=True, accept_encoding=True, user_agent=USER_AGENT
    )

    def __init__(self, insert_key, host=None, port=443):
        host = host or self.HOST
        headers = self.HEADERS.copy()
        headers.update(
            {
                "Api-Key": insert_key,
                "Content-Encoding": "gzip",
                "Content-Type": "application/json",
            }
        )
        retries = urllib3.Retry(
            total=False, connect=None, read=None, redirect=0, status=None
        )

        # Check if https traffic should be proxied and pass the proxy
        # information to the connectionpool

        proxies = getproxies()
        proxy = proxies.get("https", None)
        proxy_headers = None
        if proxy:
            proxy = parse_url(proxy)
            _logger.info(
                "Using proxy host={0!r} port={1!r}".format(proxy.host, proxy.port)
            )
            if proxy.scheme.lower() != "http":
                _logger.warning(
                    "Contacting https destinations through "
                    "{} proxies is not supported.".format(proxy.scheme)
                )
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

        self._pool = self.POOL_CLS(
            host=host,
            port=port,
            retries=retries,
            headers=headers,
            strict=True,
            _proxy=proxy,
            _proxy_headers=proxy_headers,
        )
        self._headers = self._pool.headers

    def add_version_info(self, product, product_version):
        """Adds product and version information to a User-Agent header

        This method implements
        https://tools.ietf.org/html/rfc7231#section-5.5.3

        :param product: The product name using the SDK
        :type product: str
        :param product_version: The version string of the product in use
        :type product_version: str
        """
        product_ua_header = " {}/{}".format(product, product_version)
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

    def send(self, item):
        """Send a single item

        :param item: The object to send
        :type item: dict

        :rtype: HTTPResponse
        """
        return self.send_batch((item,))

    def send_batch(self, items, common=None):
        """Send a batch of items

        :param items: An iterable of items to send to New Relic.
        :type items: list or tuple
        :param common: (optional) A map of attributes that will be set on each
            item.
        :type common: dict

        :rtype: HTTPResponse
        """
        # Specifying the headers argument overrides any base headers existing
        # in the pool, so we must copy all existing headers
        headers = self._headers.copy()

        # Generate a unique request ID for this request
        headers["x-request-id"] = str(uuid.uuid4())

        payload = self._create_payload(items, common)
        return self._pool.urlopen("POST", self.PATH, body=payload, headers=headers)


class SpanClient(Client):
    """HTTP Client for interacting with the New Relic Span API

    This class is used to send spans to the New Relic Span API over HTTP.

    :param insert_key: Insights insert key
    :type insert_key: str
    :param host: (optional) Override the host for the span API endpoint.
    :type host: str
    :param port: (optional) Override the port for the client.
        Default: 443
    :type port: int

    Usage::

        >>> import os
        >>> insert_key = os.environ.get("NEW_RELIC_INSERT_KEY", "")
        >>> span_client = SpanClient(insert_key)
        >>> response = span_client.send({})
        >>> span_client.close()
    """

    HOST = "trace-api.newrelic.com"
    PATH = "/trace/v1"
    PAYLOAD_TYPE = "spans"


class MetricClient(Client):
    """HTTP Client for interacting with the New Relic Metric API

    This class is used to send metrics to the New Relic Metric API over HTTP.

    :param insert_key: Insights insert key
    :type insert_key: str
    :param host: (optional) Override the host for the metric API
        endpoint.
    :type host: str
    :param port: (optional) Override the port for the client.
        Default: 443
    :type port: int

    Usage::

        >>> import os
        >>> insert_key = os.environ.get("NEW_RELIC_INSERT_KEY", "")
        >>> metric_client = MetricClient(insert_key)
        >>> response = metric_client.send({})
        >>> metric_client.close()
    """

    HOST = "metric-api.newrelic.com"
    PATH = "/metric/v1"
    PAYLOAD_TYPE = "metrics"


class EventClient(Client):
    """HTTP Client for interacting with the New Relic Event API

    This class is used to send events to the New Relic Event API over HTTP.

    :param insert_key: Insights insert key
    :type insert_key: str
    :param host: (optional) Override the host for the event API
        endpoint.
    :type host: str
    :param port: (optional) Override the port for the client.
        Default: 443
    :type port: int

    Usage::

        >>> import os
        >>> insert_key = os.environ.get("NEW_RELIC_INSERT_KEY", "")
        >>> event_client = EventClient(insert_key)
        >>> response = event_client.send({})
        >>> event_client.close()
    """

    HOST = "insights-collector.newrelic.com"
    PATH = "/v1/accounts/events"

    def _create_payload(self, items, common):
        payload = json.dumps(items)
        if not isinstance(payload, bytes):
            payload = payload.encode("utf-8")

        return self._compress_payload(payload)

    def send_batch(self, items):
        """Send a batch of items

        :param items: An iterable of items to send to New Relic.
        :type items: list or tuple

        :rtype: HTTPResponse
        """
        return super(EventClient, self).send_batch(items, None)
