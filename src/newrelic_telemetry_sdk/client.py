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
import requests
import zlib

try:
    from newrelic_telemetry_sdk.version import version
except ImportError:  # pragma: no cover
    version = "unknown"  # pragma: no cover

USER_AGENT = "NewRelic-Python-TelemetrySDK/{}".format(version)

__all__ = ("SpanClient", "MetricClient")


class Client(object):
    """HTTP Client for interacting with New Relic APIs

    This class is used to send data to the New Relic APIs over HTTP. This class
    will automatically handle retries as needed.

    :param insert_key: Insights insert key
    :type insert_key: str
    :param url: The API endpoint.
    :type url: str
    :param compression_threshold: Compress if number of bytes in payload is
        above this threshold.
    :type compression_threshold: int

    Usage::

        >>> import os
        >>> insert_key = os.environ.get("NEW_RELIC_INSERT_KEY")
        >>> client = Client(insert_key, "https://metric-api.newrelic.com/trace/v1", 0)
        >>> response = client.send({})
    """

    PAYLOAD_TYPE = ""
    GZIP_HEADER = {"Content-Encoding": "gzip"}

    def __init__(self, insert_key, url, compression_threshold):
        self.url = url
        self.compression_threshold = compression_threshold
        headers = {
            "Api-Key": insert_key,
            "User-Agent": USER_AGENT,
            "Content-Encoding": "identity",
            "Content-Type": "application/json",
        }
        session = self.session = requests.Session()
        session.headers.update(headers)

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

        :rtype: requests.Response
        """
        return self.send_batch((item,))

    def send_batch(self, items, common=None):
        """Send a batch of spans

        :param items: An iterable of items to send to New Relic.
        :type items: list or tuple

        :rtype: requests.Response
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
            headers = self.GZIP_HEADER

        return self.session.post(self.url, headers=headers, data=payload)


class SpanClient(Client):
    """HTTP Client for interacting with the New Relic Span API

    This class is used to send spans to the New Relic Span API over HTTP.

    :param insert_key: Insights insert key
    :type insert_key: str
    :param host: (optional) Override the host for the span API endpoint.
    :type host: str
    :param compression_threshold: Compress if number of bytes in payload is
        above this threshold. (Default: 64K)
    :type compression_threshold: int

    Usage::

        >>> import os
        >>> insert_key = os.environ.get("NEW_RELIC_INSERT_KEY")
        >>> span_client = SpanClient(insert_key)
        >>> response = span_client.send({})
    """

    HOST = "trace-api.newrelic.com"
    URL_TEMPLATE = "https://{0}/trace/v1"
    PAYLOAD_TYPE = "spans"

    def __init__(self, insert_key, host=None, compression_threshold=64 * 1024):
        host = host or self.HOST
        url = self.URL_TEMPLATE.format(host)
        super(SpanClient, self).__init__(insert_key, url, compression_threshold)


class MetricClient(Client):
    """HTTP Client for interacting with the New Relic Metric API

    This class is used to send metrics to the New Relic Metric API over HTTP.

    :param insert_key: Insights insert key
    :type insert_key: str
    :param metric_host: (optional) Override the host for the metric API
        endpoint.
    :type metric_host: str
    :param compression_threshold: Compress if number of bytes in payload is
        above this threshold. (Default: 64K)
    :type compression_threshold: int

    Usage::

        >>> import os
        >>> insert_key = os.environ.get("NEW_RELIC_INSERT_KEY")
        >>> metric_client = MetricClient(insert_key)
        >>> response = metric_client.send({})
    """

    HOST = "metric-api.newrelic.com"
    URL_TEMPLATE = "https://{0}/metric/v1"
    PAYLOAD_TYPE = "metrics"

    def __init__(self, insert_key, host=None, compression_threshold=64 * 1024):
        host = host or self.HOST
        url = self.URL_TEMPLATE.format(host)
        super(MetricClient, self).__init__(insert_key, url, compression_threshold)
