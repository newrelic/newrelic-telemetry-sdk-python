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

import random
import time


class Span(dict):
    """A span represented in the New Relic Distributed Tracing UI

    This data structure represents a single event with duration as part of a
    distributed trace. Generally, this class should be used as a context
    manager.

    :param name: The name of the span.
    :type name: str
    :param tags: (optional) A set of tags that can be used to filter this span
        in the New Relic UI.
    :type tags: dict
    :param guid: (optional) A random, unique identifier used to locate exactly
        1 span in New Relic. This must be a unique identifier across all spans
        in a New Relic account.
    :type guid: str
    :param trace_id: (optional) A random identifier representing a group of
        spans known as a "trace". Spans having the same trace_id are grouped
        into a single view.
    :type trace_id: str
    :param parent_id: (optional) The guid of the span that called this span.
    :type parent_id: str
    :param start_time_ms: (optional) A unix timestamp in milliseconds
        representing the start time of the span. Defaults to time.time() * 1000
    :type start_time_ms: int
    :param duration_ms: (optional) Total duration of the span in milliseconds.
    :type duration_ms: int

    Usage::

        >>> import newrelic_telemetry_sdk
        >>> with newrelic_telemetry_sdk.Span('span_name') as s:
        ...     pass
    """

    def __init__(
        self,
        name,
        tags=None,
        guid=None,
        trace_id=None,
        parent_id=None,
        start_time_ms=None,
        duration_ms=None,
    ):
        self["id"] = guid or ("%016x" % random.getrandbits(64))
        self["trace.id"] = trace_id or ("%016x" % random.getrandbits(64))
        self["timestamp"] = int(start_time_ms or (time.time() * 1000))

        attributes = tags and tags.copy() or {}
        self["attributes"] = attributes

        attributes["name"] = name

        if duration_ms is not None:
            attributes["duration.ms"] = int(duration_ms)

        if parent_id:
            attributes["parent.id"] = parent_id

    def finish(self, finish_time_ms=None):
        """Record the duration on this span.

        :param finish_time_ms: (optional) Timestamp in milliseconds. Defaults
            to time.time() * 1000
        :type finish_time_ms: int
        """
        finish_time_ms = int(finish_time_ms or (time.time() * 1000))
        self["attributes"]["duration.ms"] = finish_time_ms - self["timestamp"]

    def __enter__(self):
        return self

    def __exit__(self, exc, value, tb):
        self.finish()
