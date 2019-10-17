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


class Metric(dict):
    """Base Metric type

    Includes common method definitions and implementations for metrics.

    :param name: The name of the metric.
    :type name: str
    :param value: The metric value.
    :type value: int or float
    :param tags: (optional) A set of tags that can be used to filter this
        metric in the New Relic UI.
    :type tags: dict
    :param interval_ms: (optional) The interval of time in milliseconds over which
        the metric was recorded.
    :type interval_ms: int
    :param end_time_ms: (optional) A unix timestamp in milliseconds representing the
        end time_ms of the metric. Defaults to time.time() * 1000
    :type end_time_ms: int
    """

    def __init__(self, name, value, tags=None, interval_ms=None, end_time_ms=None):
        self["name"] = name
        self["value"] = value

        if interval_ms is not None:
            interval = self["interval.ms"] = int(interval_ms)
        else:
            interval = 0

        self["timestamp"] = int(end_time_ms or (time.time() * 1000)) - interval

        if tags:
            self["attributes"] = tags

    def copy(self):
        cls = type(self)
        d = cls.__new__(cls)
        d.update(self)
        return d

    @property
    def name(self):
        """Metric Name"""
        return self["name"]

    @property
    def value(self):
        """Metric Value"""
        return self["value"]

    @property
    def interval_ms(self):
        """Metric Interval"""
        if "interval.ms" in self:
            return self["interval.ms"]

    @property
    def start_time_ms(self):
        """Metric timestamp"""
        return self["timestamp"]

    @property
    def end_time_ms(self):
        """Metric timestamp"""
        return self["timestamp"] + self.get("interval.ms", 0)

    @property
    def tags(self):
        """Metric Tags"""
        return self.get("attributes")

    @classmethod
    def from_value(cls, name, value, tags=None, interval_ms=None, end_time_ms=None):
        return cls(
            name=name,
            value=value,
            tags=tags,
            interval_ms=interval_ms,
            end_time_ms=end_time_ms,
        )


class GaugeMetric(Metric):
    """Basic Metric type

    This metric is of a "gauge" type. It records values at a point in time.

    :param name: The name of the metric.
    :type name: str
    :param value: The metric value.
    :type value: int or float
    :param tags: (optional) A set of tags that can be used to filter this
        metric in the New Relic UI.
    :type tags: dict
    :param interval_ms: (optional) The interval of time in milliseconds over which
        the metric was recorded.
    :type interval_ms: int
    :param end_time_ms: (optional) A unix timestamp in milliseconds representing the
        end time of the metric. Defaults to time.time() * 1000
    :type end_time_ms: int

    Usage::

        >>> from newrelic_telemetry_sdk import GaugeMetric
        >>> metric = GaugeMetric('temperature', 20, tags={'units': 'C'})
        >>> metric.value
        20
    """


class CountMetric(Metric):
    """Count Metric

    This metric is of a "count" type. The metric holds an integer indicating a
    count of events which have taken place.

    :param name: The name of the metric.
    :type name: str
    :param value: The metric count value.
    :type value: int or float
    :param tags: (optional) A set of tags that can be used to filter this
        metric in the New Relic UI.
    :type tags: dict
    :param interval_ms: (optional) The interval of time in milliseconds over which
        the metric was recorded.
    :type interval_ms: int
    :param end_time_ms: (optional) A unix timestamp in milliseconds representing the
        end time of the metric. Defaults to time.time() * 1000
    :type end_time_ms: int

    Usage::

        >>> from newrelic_telemetry_sdk import CountMetric
        >>> metric = CountMetric('response_status', 0, tags={'code': 200})
        >>> metric.value
        0
    """

    def __init__(self, name, value, tags=None, interval_ms=None, end_time_ms=None):
        super(CountMetric, self).__init__(name, value, tags, interval_ms, end_time_ms)

        self["type"] = "count"


class SummaryMetric(Metric):
    """Summary Metric

    This metric is of a "summary" type. It tracks the count, sum, min, and
    max values when recording values. These values can be used to compute
    averages and distributions over time.

    :param name: The name of the metric.
    :type name: str
    :param count: The count in the summary metric.
    :type count: int
    :param sum: The sum in the summary metric.
    :type sum: int or float
    :param min: The minimum value in the summary metric.
    :type min: int or float
    :param max: The maximum value in the summary metric.
    :type max: int or float
    :param tags: (optional) A set of tags that can be used to filter this
        metric in the New Relic UI.
    :type tags: dict
    :param interval_ms: (optional) The interval of time in milliseconds over which
        the metric was recorded.
    :type interval_ms: int
    :param end_time_ms: (optional) A unix timestamp in milliseconds representing the
        end time of the metric. Defaults to time.time() * 1000
    :type end_time_ms: int

    Usage::

        >>> from newrelic_telemetry_sdk import SummaryMetric
        >>> metric = SummaryMetric.from_value('response_time', 0.2)
        >>> sorted(metric.value.items())
        [('count', 1), ('max', 0.2), ('min', 0.2), ('sum', 0.2)]
    """

    def __init__(
        self, name, count, sum, min, max, tags=None, interval_ms=None, end_time_ms=None
    ):
        value = {"count": count, "sum": sum, "min": min, "max": max}
        super(SummaryMetric, self).__init__(name, value, tags, interval_ms, end_time_ms)
        self["type"] = "summary"

    @classmethod
    def from_value(cls, name, value, tags=None, interval_ms=None, end_time_ms=None):
        """Create a SummaryMetric with a single value

        :param name: The name of the metric.
        :type name: str
        :param value: The metric value.
        :type value: int or float
        :param tags: (optional) A set of tags that can be used to filter this
            metric in the New Relic UI.
        :type tags: dict
        :param interval_ms: (optional) The interval of time in milliseconds over which
            the metric was recorded.
        :type interval_ms: int
        :param end_time_ms: (optional) A unix timestamp in milliseconds representing
            the end time of the metric. Defaults to time.time() * 1000
        :type end_time_ms: int
        """
        return cls(
            name=name,
            count=1,
            sum=value,
            min=value,
            max=value,
            tags=tags,
            interval_ms=interval_ms,
            end_time_ms=end_time_ms,
        )
