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

import pytest
from utils import CustomMapping

from newrelic_telemetry_sdk.metric import CountMetric, GaugeMetric, Metric, SummaryMetric


def test_gauge_metric_defaults(freeze_time):
    metric = GaugeMetric("name", 0)
    assert metric["name"] == "name"
    assert metric["value"] == 0
    assert metric["timestamp"] == 2000
    assert type(metric["timestamp"]) is int

    assert "type" not in metric
    assert "interval.ms" not in metric
    assert "attributes" not in metric


def test_count_metric_defaults(freeze_time):
    metric = CountMetric("name", 0, 0)
    assert metric["type"] == "count"
    assert metric["name"] == "name"
    assert metric["value"] == 0
    assert metric["interval.ms"] == 0
    assert type(metric["interval.ms"]) is int
    assert metric["timestamp"] == 2000
    assert type(metric["timestamp"]) is int

    assert "attributes" not in metric


def test_summary_metric_defaults(freeze_time):
    metric = SummaryMetric("name", 0, 0, 0, 0, 0)
    assert metric["type"] == "summary"
    assert metric["name"] == "name"
    assert metric["value"] == {"count": 0, "sum": 0, "min": 0, "max": 0}
    assert metric["interval.ms"] == 0
    assert type(metric["interval.ms"]) is int
    assert metric["timestamp"] == 2000
    assert type(metric["timestamp"]) is int

    assert "attributes" not in metric


@pytest.mark.parametrize(
    "arg_name,arg_value,metric_key,metric_value",
    (
        ("tags", {"foo": "bar"}, "attributes", {"foo": "bar"}),
        ("tags", CustomMapping(), "attributes", {"foo": "bar"}),
        ("end_time_ms", 1000, "timestamp", 1000),
    ),
)
def test_metric_optional(arg_name, arg_value, metric_key, metric_value):
    kwargs = {arg_name: arg_value}
    metric = Metric("foo", 3, 0, **kwargs)
    assert metric.name == "foo"
    assert metric.value == 3
    assert metric.interval_ms == 0
    assert metric[metric_key] == metric_value
    assert type(metric[metric_key]) is type(metric_value)


@pytest.mark.parametrize(
    "kwargs, metric_key, attribute_name",
    (
        ({"name": "a", "value": 0, "interval_ms": None}, "interval.ms", "interval_ms"),
        ({"name": "a", "value": 0, "interval_ms": 0, "end_time_ms": None}, "timestamp", "start_time_ms"),
        ({"name": "a", "value": 0, "interval_ms": 0, "end_time_ms": None}, "timestamp", "end_time_ms"),
    ),
)
def test_metric_none(kwargs, metric_key, attribute_name):
    metric = Metric(**kwargs)
    assert metric_key not in metric
    assert getattr(metric, attribute_name) is None


@pytest.mark.parametrize(
    "attribute_name,attribute_value",
    (
        ("name", "foo"),
        ("value", 8),
        ("tags", {"tag": "value"}),
        ("interval_ms", 1000),
        ("interval_ms", None),
        ("start_time_ms", 1000),
        ("end_time_ms", 2000),
    ),
)
def test_metric_accessors(attribute_name, attribute_value):
    if attribute_name == "interval_ms" and attribute_value is None:  # noqa: SIM108
        interval = None
    else:
        interval = 1000

    metric = CountMetric("foo", 8, tags={"tag": "value"}, interval_ms=interval, end_time_ms=2000)
    value = getattr(metric, attribute_name)
    assert value == attribute_value
    assert type(value) is type(attribute_value)

    # Verify that end_time_ms uses default interval of 0
    if interval is None:
        assert metric.end_time_ms == 2000


def test_metric_copy():
    original = GaugeMetric("foo", "bar")

    copy = original.copy()
    assert copy == original
    assert copy is not original
