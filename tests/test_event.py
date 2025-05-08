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

from newrelic_telemetry_sdk.event import Event


def test_event_defaults(freeze_time):
    event = Event("event")
    assert event == {"eventType": "event", "timestamp": 2000}
    assert type(event["timestamp"]) is int


@pytest.mark.parametrize(
    "arg_name,arg_value,event_key,event_value",
    (("tags", {"foo": "bar"}, ("foo",), "bar"), ("timestamp_ms", 1000, ("timestamp",), 1000)),
)
def test_event_optional(arg_name, arg_value, event_key, event_value):
    kwargs = {arg_name: arg_value}
    event = Event("event", **kwargs)

    value = event
    for key in event_key:
        value = value[key]

    assert value == event_value
    assert type(value) is type(event_value)


@pytest.mark.parametrize("attribute_name,attribute_value", (("event_type", "event"), ("timestamp_ms", 1000)))
def test_event_attributes(attribute_name, attribute_value):
    event = Event("event", timestamp_ms=1000)
    value = getattr(event, attribute_name)
    assert value == attribute_value
    assert type(value) is type(attribute_value)


def test_event_copy():
    original = Event("event")
    copy = original.copy()
    assert copy == original
    assert copy is not original


def test_intrinsics_override_user_attributes():
    tags = {"eventType": "illegal"}
    event = Event("event", tags)
    assert event["eventType"] == "event"
