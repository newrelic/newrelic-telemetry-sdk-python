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

import time

import pytest
from utils import CustomMapping

from newrelic_telemetry_sdk.metric_batch import MetricBatch


class VerifyLockMetricBatch(MetricBatch):
    """Verify sensitive attributes are accessed / assigned under lock

    These attributes are sensitive and should only be accessed under lock.
    NOTE: It doesn't guarantee that the values returned are only modified under
    lock; however, this provides some level of checking.
    """

    @property
    def _batch(self):
        assert self._lock.locked()
        return self._internal_batch

    @_batch.setter
    def _batch(self, value):
        if hasattr(self, "_internal_batch"):
            assert self._lock.locked()
        self._internal_batch = value

    @property
    def _interval_start(self):
        assert self._lock.locked()
        return self._internal_interval_start

    @_interval_start.setter
    def _interval_start(self, value):
        if hasattr(self, "_internal_interval_start"):
            assert self._lock.locked()
        self._internal_interval_start = value

    @property
    def _common(self):
        return self._internal_common

    @_common.setter
    def _common(self, value):
        # This attribute should never be assigned
        assert not hasattr(self, "_internal_common")
        self._internal_common = value


@pytest.mark.parametrize("tags", (None, {"foo": "bar"}))
def test_create_identity(tags):
    expected_tags = frozenset(tags.items()) if tags else None
    identity = MetricBatch.create_identity("name", tags)
    assert len(identity) == 3
    assert identity[0] is None
    assert identity[1] == "name"
    assert identity[2] == expected_tags


@pytest.mark.parametrize(
    "record_method, value_1, value_2, final_value",
    (
        ("record_gauge", 1, 2, 2),
        ("record_count", 1, 2, 3),
        ("record_summary", 1, 2, {"count": 2, "max": 2, "min": 1, "sum": 3}),
    ),
)
def test_merge_metric(record_method, value_1, value_2, final_value):
    batch = VerifyLockMetricBatch()

    record_method = getattr(batch, record_method)
    record_method("name", value_1)
    record_method("name", value_2)

    assert len(batch._internal_batch) == 1
    identity, value = batch._internal_batch.popitem()

    assert identity[1] == "name"
    assert value == final_value


@pytest.mark.parametrize(
    "metric_a, metric_b",
    (
        (("record_gauge", "name", 1, None), ("record_count", "name", 1, None)),
        (("record_gauge", "foo", 1, None), ("record_gauge", "bar", 1, None)),
        (("record_gauge", "foo", 1, {"foo": 1}), ("record_gauge", "foo", 1, {"foo": 2})),
    ),
)
def test_different_metric(metric_a, metric_b):
    batch = VerifyLockMetricBatch()

    record_method_a = getattr(batch, metric_a[0])
    record_method_b = getattr(batch, metric_b[0])

    record_method_a(*metric_a[1:])
    record_method_b(*metric_b[1:])

    assert len(batch._internal_batch) == 2


@pytest.mark.parametrize("tags", (None, {"foo": "bar"}, CustomMapping()))
def test_flush(monkeypatch, tags):
    delta = 4.0
    current_t = [1.0]

    def _time():
        # Move time forward by delta on every call
        current_t[0] *= delta
        return current_t[0]

    monkeypatch.setattr(time, "time", _time, raising=True)

    # NOTE: calls time.time() to record start time
    # t = 4
    batch = VerifyLockMetricBatch(tags)
    batch.record_count("count", 1, tags={"foo": "bar"})

    # Timestamp starts at 4
    assert batch._internal_interval_start == 4000

    # NOTE: record_gauge calls time.time() to record timestamp
    # t = 16
    batch.record_gauge("gauge", 8)

    # NOTE: calls time.time() as new batch start time
    # t = 64
    metrics, common = batch.flush()

    assert len(metrics) == 2
    for metric in metrics:
        if metric["name"] == "gauge":
            assert "type" not in metric
            assert metric["timestamp"] == 16000
            assert metric["value"] == 8
        elif metric["name"] == "count":
            assert "timestamp" not in metric
            assert metric["type"] == "count"
            assert metric["attributes"] == {"foo": "bar"}
            assert metric["value"] == 1
        else:
            raise AssertionError(f"Unexpected metric type: {metric}")

    assert common["timestamp"] == 4000
    assert common["interval.ms"] == 60000
    if tags:
        assert common["attributes"] == dict(tags)
    else:
        assert "attributes" not in common

    # Verify internal state is updated
    assert batch._internal_interval_start > 0
    assert batch._internal_batch == {}

    # Verify that we don't return the same objects twice
    assert batch.flush()[1] is not common
