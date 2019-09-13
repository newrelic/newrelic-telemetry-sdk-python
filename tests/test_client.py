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
import pytest
import os
import time
import uuid
import zlib
from newrelic_telemetry_sdk.version import version
from newrelic_telemetry_sdk.client import SpanClient, MetricClient
from requests.adapters import HTTPAdapter
from requests.models import Response

try:
    string_types = basestring
except NameError:
    string_types = str

SPAN = {
    "id": str(uuid.uuid4()),
    "trace.id": "trace.id",
    "attributes": {
        "name": "testing",
        "timestamp": int(time.time() * 1000.0),
        "duration.ms": 1,
        "service.name": "testing",
    },
}

METRIC = {
    "name": "testing",
    "type": "count",
    "value": 1,
    "timestamp": int(time.time() - 1),
    "interval.ms": 1000,
}


def disable_sending(self, request, *args, **kwargs):
    response = Response()
    response.status_code = 200
    response.request = request
    return response


@pytest.fixture
def span_client(request, monkeypatch):
    host = os.environ.get("NEW_RELIC_HOST", "")
    insert_key = os.environ.get("NEW_RELIC_INSERT_KEY", "")

    if host.startswith("staging"):
        host = "staging-trace-api.newrelic.com"

    if not insert_key:
        monkeypatch.setattr(HTTPAdapter, "send", disable_sending)

    # Allow client_args to be specified by a marker
    client_args = request.node.get_closest_marker("client_args")
    if client_args:
        return SpanClient(insert_key, host, *client_args.args, **client_args.kwargs)
    else:
        return SpanClient(insert_key, host)


@pytest.fixture
def metric_client(request, monkeypatch):
    host = os.environ.get("NEW_RELIC_HOST", "")
    insert_key = os.environ.get("NEW_RELIC_INSERT_KEY", "")

    if host.startswith("staging"):
        host = "staging-metric-api.newrelic.com"

    if not insert_key:
        monkeypatch.setattr(HTTPAdapter, "send", disable_sending)

    # Allow client_args to be specified by a marker
    client_args = request.node.get_closest_marker("client_args")
    if client_args:
        return MetricClient(insert_key, host, *client_args.args, **client_args.kwargs)
    else:
        return MetricClient(insert_key, host)


def ensure_str(s):
    if not isinstance(s, string_types):
        try:
            s = s.decode("utf-8")
        except Exception:
            return
    return s


def decompress(payload):
    decompressor = zlib.decompressobj(31)
    payload = decompressor.decompress(payload)
    payload += decompressor.flush()
    return payload


def validate_request(legal_urls, typ, request, items, common=None):
    # request method should be POST
    assert request.method == "POST"

    # Validate that the user agent string is correct
    user_agent = request.headers["User-Agent"]
    assert user_agent.startswith("NewRelic-Python-TelemetrySDK/")
    assert version in user_agent

    # Validate payload is compressed JSON
    assert request.headers["Content-Type"] == "application/json"

    # Validate the URL
    assert request.url in legal_urls

    headers = request.headers
    assert "Api-Key" in headers

    payload = request.body
    assert "Content-Encoding" in request.headers

    if request.headers["Content-Encoding"] == "gzip":
        # Decompress the payload
        payload = decompress(request.body)
    else:
        assert request.headers["Content-Encoding"] == "identity"

    # payload is always in the form [{typ: ..., '...'}]
    payload = json.loads(ensure_str(payload))
    assert len(payload) == 1
    payload = payload[0]

    if common:
        expected_len = 2
    else:
        expected_len = 1
    assert len(payload) == expected_len

    assert payload[typ] == items
    if common:
        assert payload["common"] == common


def validate_span_request(request, items, common=None):
    validate_request(
        (
            "https://trace-api.newrelic.com/trace/v1",
            "https://staging-trace-api.newrelic.com/trace/v1",
        ),
        "spans",
        request,
        items,
        common,
    )


def validate_metric_request(request, items, common=None):
    validate_request(
        (
            "https://metric-api.newrelic.com/metric/v1",
            "https://staging-metric-api.newrelic.com/metric/v1",
        ),
        "metrics",
        request,
        items,
        common,
    )


@pytest.mark.client_args(compression_threshold=0)
def test_span_endpoint_compressed(span_client):
    response = span_client.send(SPAN)
    request = response.request
    assert "Content-Encoding" in request.headers
    validate_span_request(request, [SPAN])


@pytest.mark.client_args(compression_threshold=float("inf"))
def test_span_endpoint_uncompressed(span_client):
    response = span_client.send(SPAN)
    request = response.request
    assert request.headers["Content-Encoding"] == "identity"
    validate_span_request(request, [SPAN])


@pytest.mark.client_args(compression_threshold=0)
def test_metric_endpoint_compressed(metric_client):
    response = metric_client.send(METRIC)
    request = response.request
    assert request.headers["Content-Encoding"] == "gzip"
    validate_metric_request(request, [METRIC])


@pytest.mark.client_args(compression_threshold=float("inf"))
def test_metric_endpoint_uncompressed(metric_client):
    response = metric_client.send(METRIC)
    request = response.request
    assert request.headers["Content-Encoding"] == "identity"
    validate_metric_request(request, [METRIC])


def test_metric_endpoint_batch(metric_client):
    metrics = [{"name": "testing", "type": "count", "value": 1}]
    tags = {"hostname": "localhost"}
    timestamp_ms = (time.time() - 1) * 1000.0
    interval_ms = 100.6

    common = {"attributes": tags, "interval.ms": interval_ms, "timestamp": timestamp_ms}

    response = metric_client.send_batch(metrics, common=common)
    validate_metric_request(response.request, metrics, common)


def test_span_endpoint_batch(span_client):
    spans = [
        {
            "id": str(uuid.uuid4()),
            "trace.id": "trace.id",
            "attributes": {
                "name": "testing",
                "duration.ms": 1,
                "service.name": "testing",
            },
        }
    ]
    timestamp_ms = (time.time() - 1) * 1000.0
    common = {"attributes": {"timestamp": timestamp_ms}}

    response = span_client.send_batch(spans, common=common)
    validate_span_request(response.request, spans, common)


@pytest.mark.parametrize(
    "cls,host",
    ((SpanClient, "trace-api.newrelic.com"), (MetricClient, "metric-api.newrelic.com")),
)
def test_defaults(cls, host):
    assert cls.HOST == host
    assert cls(None).compression_threshold == 64 * 1024
