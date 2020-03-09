# Copyright 2020 New Relic, Inc.
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

import pytest
from newrelic_telemetry_sdk.metric import GaugeMetric, CountMetric, SummaryMetric
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
    metric = GaugeMetric("name", 1000, tags=tags)

    expected_tags = frozenset(tags.items()) if tags else None
    identity = MetricBatch.create_identity(metric)
    assert len(identity) == 3
    assert identity[0] is GaugeMetric
    assert identity[1] == "name"
    assert identity[2] == expected_tags


@pytest.mark.parametrize(
    "metric_a, metric_b, expected_value",
    (
        (GaugeMetric("name", 1), GaugeMetric("name", 2), 2),
        (CountMetric("name", 1), CountMetric("name", 2), 3),
        (
            SummaryMetric.from_value("name", 1),
            SummaryMetric.from_value("name", 2),
            {"count": 2, "max": 2, "min": 1, "sum": 3},
        ),
    ),
)
def test_merge_metric(metric_a, metric_b, expected_value):
    batch = VerifyLockMetricBatch()

    batch.record(metric_a)
    batch.record(metric_b)

    assert metric_a.start_time_ms
    assert metric_b.start_time_ms

    assert len(batch._internal_batch) == 1
    _, metric = batch._internal_batch.popitem()

    assert metric.name == "name"
    assert metric.value == expected_value
    assert "timestamp" not in metric


@pytest.mark.parametrize("tags", (None, {"foo": "bar"},))
def test_flush(tags):
    metric = GaugeMetric("name", 1)
    batch = VerifyLockMetricBatch(tags)
    batch.record(metric)

    # Initialize with dummy timestamp to verify timestamp update
    batch._internal_interval_start = 0

    metrics, common = batch.flush()

    assert len(metrics) == 1

    assert common["timestamp"] == 0
    assert common["interval.ms"] > 0
    if tags:
        assert common["attributes"] == tags
    else:
        assert "attributes" not in common

    # Verify internal state is updated
    assert batch._internal_interval_start > 0
    assert batch._internal_batch == {}

    # Verify that we don't return the same objects twice
    assert batch.flush()[1] is not common
