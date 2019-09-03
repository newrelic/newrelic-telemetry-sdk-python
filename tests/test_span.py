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
from newrelic_telemetry_sdk.span import Span


def test_span_defaults(freeze_time):
    span = Span("name")
    attributes = span["attributes"]
    assert attributes["name"] == "name"
    assert len(attributes) == 1

    # Verify timestamp intrinsic
    assert span["timestamp"] == 2000
    assert type(span["timestamp"]) is int

    # Verify guid-type values
    assert type(span["id"]) is str
    int(span["id"], 16)
    assert len(span["id"]) == 16

    assert type(span["trace.id"]) is str
    int(span["trace.id"], 16)
    assert len(span["trace.id"]) == 16


@pytest.mark.parametrize(
    "arg_name,arg_value,span_key,span_value",
    (
        ("guid", "foo", ("id",), "foo"),
        ("trace_id", "foo", ("trace.id",), "foo"),
        ("start_time_ms", 1500.0, ("timestamp",), 1500),
        ("duration_ms", 1500.0, ("attributes", "duration.ms"), 1500),
        ("parent_id", "parent", ("attributes", "parent.id"), "parent"),
        ("tags", {"foo": "bar"}, ("attributes", "foo"), "bar"),
    ),
)
def test_span_optional(arg_name, arg_value, span_key, span_value):
    kwargs = {arg_name: arg_value}
    span = Span("name", **kwargs)

    value = span
    for key in span_key:
        value = value[key]

    assert value == span_value
    assert type(value) is type(span_value)


def test_span_finish_without_argument(freeze_time):
    span = Span("name", start_time_ms=1000.0)
    span.finish()
    value = span["attributes"]["duration.ms"]
    assert value == 1000
    assert isinstance(value, int)


def test_span_finish_with_argument(freeze_time):
    span = Span("name")
    span.finish(3000.0)
    value = span["attributes"]["duration.ms"]
    assert value == 1000
    assert isinstance(value, int)


def test_span_context_manager(freeze_time):
    span = Span("name", start_time_ms=1000.0)
    with span:
        pass

    value = span["attributes"]["duration.ms"]
    assert value == 1000
    assert isinstance(value, int)


def test_span_duration_zero():
    span = Span("name", duration_ms=0)

    value = span["attributes"]["duration.ms"]
    assert value == 0
    assert isinstance(value, int)
