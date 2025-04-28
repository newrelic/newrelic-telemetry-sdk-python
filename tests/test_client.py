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

import functools
import json
import os
import time
import uuid
import zlib

import pytest
from urllib3 import HTTPConnectionPool, Retry
from urllib3 import HTTPResponse as URLLib3HTTPResponse

from newrelic_telemetry_sdk.client import EventClient, HTTPError, HTTPResponse, LogClient, MetricClient, SpanClient
from newrelic_telemetry_sdk.version import version

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

METRIC = {"name": "testing", "type": "count", "value": 1, "timestamp": int(time.time() - 1), "interval.ms": 1000}

EVENT = {"eventType": "testing"}

LOG = {"timestamp": int(time.time() * 1000.0), "message": "Hello world"}


class Request:
    def __init__(self, wrapped, method, url, body=None, headers=None, *args, **kwargs):
        assert isinstance(headers, dict) or headers is None
        headers = headers or wrapped.headers
        self.method = method
        self.url = url
        self.body = body
        self.headers = headers
        self.args = args
        self.kwargs = kwargs


def capture_request(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        response = fn(*args, **kwargs)
        response.request = Request(*args, **kwargs)
        return response

    return wrapper


def disable_sending(*args, **kwargs):
    urllib3_response = URLLib3HTTPResponse(status=202)
    urllib3_response.request = Request(*args, **kwargs)
    return HTTPResponse(urllib3_response)


def test_response_json():
    urllib3_response = URLLib3HTTPResponse(status=200, body=b"{}")
    response = HTTPResponse(urllib3_response)
    assert response.json() == {}


@pytest.mark.parametrize("status,expected", ((199, False), (200, True), (299, True), (300, False)))
def test_response_ok(status, expected):
    urllib3_response = URLLib3HTTPResponse(status=status)
    response = HTTPResponse(urllib3_response)
    assert response.ok is expected


def test_response_raise_for_status_error():
    urllib3_response = URLLib3HTTPResponse(status=500)
    response = HTTPResponse(urllib3_response)
    with pytest.raises(HTTPError):
        response.raise_for_status()


def test_response_raise_for_status_ok():
    urllib3_response = URLLib3HTTPResponse(status=200)
    response = HTTPResponse(urllib3_response)
    response.raise_for_status()


def test_wrapped_response_attributes_available():
    urllib3_response = URLLib3HTTPResponse(status=200)
    response = HTTPResponse(urllib3_response)
    assert response.status == 200


@pytest.fixture
def span_client(request, monkeypatch):
    host = os.environ.get("NEW_RELIC_HOST", "")
    license_key = os.environ.get("NEW_RELIC_LICENSE_KEY", "test-key")

    if host.startswith("staging"):
        host = "staging-trace-api.newrelic.com"

    if license_key:
        urlopen = HTTPConnectionPool.urlopen
        monkeypatch.setattr(HTTPConnectionPool, "urlopen", capture_request(urlopen))
    else:
        monkeypatch.setattr(HTTPConnectionPool, "urlopen", disable_sending)

    # Allow client_args to be specified by a marker
    client_args = request.node.get_closest_marker("client_args")
    if client_args:
        client = SpanClient(license_key, host, *client_args.args, **client_args.kwargs)
    else:
        client = SpanClient(license_key, host)

    assert client._pool.port == 443
    yield client
    client.close()


@pytest.fixture
def metric_client(request, monkeypatch):
    host = os.environ.get("NEW_RELIC_HOST", "")
    license_key = os.environ.get("NEW_RELIC_LICENSE_KEY", "test-key")

    if host.startswith("staging"):
        host = "staging-metric-api.newrelic.com"

    if license_key:
        urlopen = HTTPConnectionPool.urlopen
        monkeypatch.setattr(HTTPConnectionPool, "urlopen", capture_request(urlopen))
    else:
        monkeypatch.setattr(HTTPConnectionPool, "urlopen", disable_sending)

    # Allow client_args to be specified by a marker
    client_args = request.node.get_closest_marker("client_args")
    if client_args:
        client = MetricClient(license_key, host, *client_args.args, **client_args.kwargs)
    else:
        client = MetricClient(license_key, host)

    assert client._pool.port == 443
    yield client
    client.close()


@pytest.fixture
def log_client(request, monkeypatch):
    host = os.environ.get("NEW_RELIC_HOST", "")
    license_key = os.environ.get("NEW_RELIC_LICENSE_KEY", "test-key")

    if host.startswith("staging"):
        host = "staging-log-api.newrelic.com"

    if license_key:
        urlopen = HTTPConnectionPool.urlopen
        monkeypatch.setattr(HTTPConnectionPool, "urlopen", capture_request(urlopen))
    else:
        monkeypatch.setattr(HTTPConnectionPool, "urlopen", disable_sending)

    # Allow client_args to be specified by a marker
    client_args = request.node.get_closest_marker("client_args")
    if client_args:
        client = LogClient(license_key, host, *client_args.args, **client_args.kwargs)
    else:
        client = LogClient(license_key, host)

    assert client._pool.port == 443
    yield client
    client.close()


@pytest.fixture
def event_client(request, monkeypatch):
    host = os.environ.get("NEW_RELIC_HOST", "")
    license_key = os.environ.get("NEW_RELIC_LICENSE_KEY", "test-key")

    if host.startswith("staging"):
        host = "staging-insights-collector.newrelic.com"

    if license_key:
        urlopen = HTTPConnectionPool.urlopen
        monkeypatch.setattr(HTTPConnectionPool, "urlopen", capture_request(urlopen))
    else:
        monkeypatch.setattr(HTTPConnectionPool, "urlopen", disable_sending)

    # Allow client_args to be specified by a marker
    client_args = request.node.get_closest_marker("client_args")
    if client_args:
        client = EventClient(license_key, host, *client_args.args, **client_args.kwargs)
    else:
        client = EventClient(license_key, host)

    assert client._pool.port == 443
    yield client
    client.close()


def ensure_str(s):
    if not isinstance(s, str):
        try:
            s = s.decode("utf-8")
        except Exception:
            return None
    return s


def decompress(payload):
    decompressor = zlib.decompressobj(31)
    payload = decompressor.decompress(payload)
    payload += decompressor.flush()
    return payload


def extract_and_validate_metadata(expected_url, request):
    # request method should be POST
    assert request.method == "POST"

    # Connection should be keep-alive
    assert request.headers["connection"] == "keep-alive"

    # Should accept gzip and deflate encoding
    assert request.headers["accept-encoding"] == "gzip,deflate"

    # Validate that the user agent string is correct
    user_agent = request.headers["user-agent"]
    assert user_agent.startswith("NewRelic-Python-TelemetrySDK/")
    assert version in user_agent

    # Validate that the x-request-id header is present and is a valid UUID4
    request_id = request.headers["x-request-id"]
    assert uuid.UUID(request_id).version == 4

    # Validate payload is compressed JSON
    assert request.headers["Content-Type"] == "application/json"

    # Validate the URL
    assert request.url == expected_url

    headers = request.headers
    assert "Api-Key" in headers

    payload = request.body
    assert "Content-Encoding" in request.headers

    if request.headers["Content-Encoding"] == "gzip":
        # Decompress the payload
        payload = decompress(request.body)
    else:
        assert request.headers["Content-Encoding"] == "identity"

    return json.loads(ensure_str(payload))


def validate_request(expected_url, typ, request, items, common=None):
    payload = extract_and_validate_metadata(expected_url, request)

    # payload is always in the form [{typ: ..., '...'}]
    assert len(payload) == 1
    payload = payload[0]

    expected_len = 2 if common else 1

    assert len(payload) == expected_len

    assert payload[typ] == items
    if common:
        assert payload["common"] == common


def validate_span_request(request, items, common=None):
    validate_request("/trace/v1", "spans", request, items, common)


def validate_metric_request(request, items, common=None):
    validate_request("/metric/v1", "metrics", request, items, common)


def validate_log_request(request, items, common=None):
    validate_request("/log/v1", "logs", request, items, common)


def validate_event_request(request, items):
    payload = extract_and_validate_metadata("/v1/accounts/events", request)
    assert payload == items


def test_metric_endpoint_batch(metric_client):
    metrics = [{"name": "testing", "type": "count", "value": 1}]
    tags = {"hostname": "localhost"}
    timestamp_ms = (time.time() - 1) * 1000.0
    interval_ms = 100.6

    common = {"attributes": tags, "interval.ms": interval_ms, "timestamp": timestamp_ms}

    response = metric_client.send_batch(metrics, common=common)
    validate_metric_request(response.request, metrics, common)


def test_log_endpoint_batch(log_client):
    logs = [LOG, {"message": "foobar"}]
    attributes = {"hostname": "localhost"}
    timestamp_ms = (time.time() - 1) * 1000.0

    common = {"attributes": attributes, "timestamp": timestamp_ms}

    response = log_client.send_batch(logs, common=common)
    validate_log_request(response.request, logs, common)


def test_span_endpoint_batch(span_client):
    spans = [
        {
            "id": str(uuid.uuid4()),
            "trace.id": "trace.id",
            "attributes": {"name": "testing", "duration.ms": 1, "service.name": "testing"},
        }
    ]
    timestamp_ms = (time.time() - 1) * 1000.0
    common = {"attributes": {"timestamp": timestamp_ms}}

    response = span_client.send_batch(spans, common=common)
    validate_span_request(response.request, spans, common)


def test_event_endpoint_batch(event_client):
    events = [EVENT, EVENT]

    response = event_client.send_batch(events)
    validate_event_request(response.request, events)


@pytest.mark.parametrize(
    "client_class,host",
    (
        (SpanClient, "trace-api.newrelic.com"),
        (MetricClient, "metric-api.newrelic.com"),
        (EventClient, "insights-collector.newrelic.com"),
        (LogClient, "log-api.newrelic.com"),
    ),
)
def test_defaults(client_class, host):
    assert client_class.HOST == host  # noqa: SIM300
    assert client_class("test-key")._pool.port == 443


@pytest.mark.parametrize("client_class", (SpanClient, MetricClient, EventClient, LogClient))
def test_port_override(client_class):
    assert client_class("test-key", port=8000)._pool.port == 8000


def test_metric_add_version_info(metric_client):
    metric_client.add_version_info("foo", "0.1")
    metric_client.add_version_info("bar", "0.2")
    response = metric_client.send(METRIC)
    validate_metric_request(response.request, [METRIC])
    request = response.request

    user_agent = request.headers["user-agent"]
    assert user_agent.endswith(" foo/0.1 bar/0.2"), user_agent


def test_span_add_version_info(span_client):
    span_client.add_version_info("foo", "0.1")
    span_client.add_version_info("bar", "0.2")
    response = span_client.send(SPAN)
    validate_span_request(response.request, [SPAN])
    request = response.request

    user_agent = request.headers["user-agent"]
    assert user_agent.endswith(" foo/0.1 bar/0.2"), user_agent


def test_event_add_version_info(event_client):
    event_client.add_version_info("foo", "0.1")
    event_client.add_version_info("bar", "0.2")
    response = event_client.send(EVENT)
    validate_event_request(response.request, [EVENT])
    request = response.request

    user_agent = request.headers["user-agent"]
    assert user_agent.endswith(" foo/0.1 bar/0.2"), user_agent


def test_log_add_version_info(log_client):
    log_client.add_version_info("foo", "0.1")
    log_client.add_version_info("bar", "0.2")
    response = log_client.send(LOG)
    validate_log_request(response.request, [LOG])
    request = response.request

    user_agent = request.headers["user-agent"]
    assert user_agent.endswith(" foo/0.1 bar/0.2"), user_agent


@pytest.mark.parametrize("client_class", (SpanClient, MetricClient, EventClient, LogClient))
def test_client_close(client_class):
    client = client_class("test-key", "test-host")
    assert client._pool.pool is not None

    client.close()
    assert client._pool.pool is None


@pytest.mark.parametrize("client_class", (SpanClient, MetricClient, EventClient, LogClient))
def test_client_connection_pool_kwargs(client_class):
    retries = Retry(3)  # Parameter with default value in our subclass
    maxsize = 3  # Parameter without default value in our subclass

    client = client_class("test-key", "test-host", retries=retries, maxsize=maxsize)

    assert client._pool.retries is retries
    assert client._pool.pool.maxsize == maxsize


@pytest.mark.parametrize("license_key", ("", None))
@pytest.mark.parametrize("client_class", (SpanClient, MetricClient, EventClient, LogClient))
def test_client_invalid_license_key(client_class, license_key):
    with pytest.raises(ValueError, match="Invalid license key"):
        client_class(license_key)
