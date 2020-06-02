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

import logging
import time

import pytest
from newrelic_telemetry_sdk.harvester import Harvester


class Response(object):
    status = 202
    ok = True


class FakeBatch(object):
    def __init__(self):
        self.contents = []

    def record(self, item):
        self.contents.append(item)

    def flush(self):
        contents = tuple(self.contents)
        self.contents = []
        return contents, None


class FakeClient(object):
    def __init__(self):
        self.sent = []
        self.response = Response()

    def send_batch(self, items, common=None):
        self.sent.append((items, common))
        return self.response


class ExceptionalClient(object):
    def send_batch(self, *args, **kwargs):
        raise RuntimeError("oops")


class FakeEventBatch(FakeBatch):
    def flush(self):
        results = super(FakeEventBatch, self).flush()
        return results[:1]


class FakeEventClient(FakeClient):
    def send_batch(self, items):
        return super(FakeEventClient, self).send_batch(items)


@pytest.fixture(params=((FakeClient, FakeBatch), (FakeEventClient, FakeEventBatch)))
def harvester_args(request):
    client_cls, event_cls = request.param
    return client_cls(), event_cls()


@pytest.fixture
def harvester(harvester_args):
    harvester = Harvester(*harvester_args)
    return harvester


@pytest.mark.filterwarnings("ignore:.*Harvester.record.*:DeprecationWarning")
def test_record(harvester):
    item = object()
    harvester.record(item)
    assert harvester.batch.contents == [item]


def test_run_once(harvester):
    harvester.harvest_interval = 0
    client = harvester._client
    send_batch = client.send_batch

    def shutdown_after_send(*args, **kwargs):
        result = send_batch(*args, **kwargs)
        harvester._shutdown.set()
        return result

    client.send_batch = shutdown_after_send
    item = object()
    harvester.batch.record(item)

    harvester.start()
    harvester.stop(timeout=0.1)

    assert client.sent == [((item,), None)]


def test_run_flushes_data_on_shutdown(harvester):
    client = harvester._client

    item = object()
    harvester.batch.record(item)

    # Set shutdown event
    harvester._shutdown.set()

    assert not client.sent
    harvester.start()
    harvester.stop(timeout=0.1)
    assert client.sent == [((item,), None)]


def test_empty_items_not_sent(harvester):
    client = harvester._client

    # Set shutdown event
    harvester._shutdown.set()

    harvester.start()
    harvester.stop(timeout=0.1)

    # Send is never called if the batch is empty
    assert not client.sent


def test_harvester_terminates_at_shutdown(harvester):
    client = harvester._client

    # Set the interval high enough so that send is never called unless shutdown
    # occurs
    harvester.harvest_interval = 99999
    harvester.start()

    assert harvester.is_alive()

    item = object()
    harvester.batch.record(item)

    assert not client.sent
    harvester.stop(0.1)
    assert not harvester.is_alive()
    assert client.sent == [((item,), None)]


def test_harvester_handles_send_exception(caplog):
    batch = FakeBatch()

    # Cause an exception to be raised since send_batch doesn't exist on object
    harvester = Harvester(object(), batch)

    harvester.batch.record(None)
    harvester._shutdown.set()
    harvester.start()
    harvester.stop(timeout=0.1)

    assert (
        "newrelic_telemetry_sdk.harvester",
        logging.ERROR,
        "New Relic send_batch failed with an exception.",
    ) in caplog.record_tuples


def test_harvester_send_failed(caplog, harvester):
    client = harvester._client
    client.response.status = 500
    client.response.ok = False

    harvester.batch.record(None)
    harvester._shutdown.set()
    harvester.start()
    harvester.stop(timeout=0.1)

    assert (
        "newrelic_telemetry_sdk.harvester",
        logging.ERROR,
        "New Relic send_batch failed with status code: 500",
    ) in caplog.record_tuples


def test_harvest_timing(harvester, monkeypatch):
    DELTA = 2
    current_t = [0]
    timeout = []

    def _time():
        # Move time forward by DELTA on every call
        current_t[0] += DELTA
        return current_t[0]

    def _wait(t):
        assert not timeout
        timeout.append(t)
        return True

    monkeypatch.setattr(time, "time", _time, raising=True)
    harvester._shutdown.wait = _wait

    # First call should result in full timeout
    assert harvester._wait_for_harvest()
    assert timeout.pop() == harvester.harvest_interval

    # Second call should account for the time between harvest intervals
    assert harvester._wait_for_harvest()
    assert timeout.pop() == (harvester.harvest_interval - DELTA)


def test_defaults(harvester):
    assert harvester.daemon is True
    assert harvester.harvest_interval == 5
