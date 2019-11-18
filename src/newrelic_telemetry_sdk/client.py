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
import urllib3
import zlib

try:
    from newrelic_telemetry_sdk.version import version as __version__
except ImportError:  # pragma: no cover
    __version__ = "unknown"

USER_AGENT = "NewRelic-Python-TelemetrySDK/{}".format(__version__)

__all__ = ("SpanClient", "MetricClient", "HTTPError", "HTTPResponse")


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
    :param compression_threshold: (optional) Compress if number of bytes in
        payload is above this threshold. (Default: 64K)
    :type compression_threshold: int

    Usage::

        >>> import os
        >>> insert_key = os.environ.get("NEW_RELIC_INSERT_KEY", "")
        >>> client = Client(insert_key, host="metric-api.newrelic.com")
        >>> response = client.send({})
    """

    POOL_CLS = HTTPSConnectionPool
    PAYLOAD_TYPE = ""
    HOST = ""
    URL = "/"
    GZIP_HEADER = {"Content-Encoding": "gzip"}
    HEADERS = urllib3.make_headers(
        keep_alive=True, accept_encoding=True, user_agent=USER_AGENT
    )

    def __init__(self, insert_key, host=None, compression_threshold=64 * 1024):
        host = host or self.HOST
        self.compression_threshold = compression_threshold
        headers = self.HEADERS.copy()
        headers.update(
            {
                "Api-Key": insert_key,
                "Content-Encoding": "identity",
                "Content-Type": "application/json",
            }
        )
        self._pool = pool = self.POOL_CLS(
            host=host, port=443, retries=False, headers=headers, strict=True
        )
        self._gzip_headers = gzip_headers = pool.headers.copy()
        gzip_headers.update(self.GZIP_HEADER)

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
        self._pool.headers["user-agent"] += product_ua_header
        self._gzip_headers["user-agent"] += product_ua_header

    @staticmethod
    def _compress_payload(payload):
        level = zlib.Z_DEFAULT_COMPRESSION
        compressor = zlib.compressobj(level, zlib.DEFLATED, 31)
        payload = compressor.compress(payload)
        payload += compressor.flush()
        return payload

    def send(self, item):
        """Send a single item

        :param item: The object to send
        :type item: dict

        :rtype: HTTPResponse
        """
        return self.send_batch((item,))

    def send_batch(self, items, common=None):
        """Send a batch of spans

        :param items: An iterable of items to send to New Relic.
        :type items: list or tuple

        :rtype: HTTPResponse
        """
        payload = {self.PAYLOAD_TYPE: items}
        if common:
            payload["common"] = common

        payload = json.dumps([payload])
        if not isinstance(payload, bytes):
            payload = payload.encode("utf-8")

        headers = None
        if len(payload) > self.compression_threshold:
            payload = self._compress_payload(payload)
            headers = self._gzip_headers

        return self._pool.urlopen("POST", self.URL, body=payload, headers=headers)


class SpanClient(Client):
    """HTTP Client for interacting with the New Relic Span API

    This class is used to send spans to the New Relic Span API over HTTP.

    :param insert_key: Insights insert key
    :type insert_key: str
    :param host: (optional) Override the host for the span API endpoint.
    :type host: str
    :param compression_threshold: (optional) Compress if number of bytes in
        payload is above this threshold. (Default: 64K)
    :type compression_threshold: int

    Usage::

        >>> import os
        >>> insert_key = os.environ.get("NEW_RELIC_INSERT_KEY", "")
        >>> span_client = SpanClient(insert_key)
        >>> response = span_client.send({})
    """

    HOST = "trace-api.newrelic.com"
    URL = "/trace/v1"
    PAYLOAD_TYPE = "spans"


class MetricClient(Client):
    """HTTP Client for interacting with the New Relic Metric API

    This class is used to send metrics to the New Relic Metric API over HTTP.

    :param insert_key: Insights insert key
    :type insert_key: str
    :param host: (optional) Override the host for the metric API
        endpoint.
    :type host: str
    :param compression_threshold: (optional) Compress if number of bytes in
        payload is above this threshold. (Default: 64K)
    :type compression_threshold: int

    Usage::

        >>> import os
        >>> insert_key = os.environ.get("NEW_RELIC_INSERT_KEY", "")
        >>> metric_client = MetricClient(insert_key)
        >>> response = metric_client.send({})
    """

    HOST = "metric-api.newrelic.com"
    URL = "/metric/v1"
    PAYLOAD_TYPE = "metrics"
