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

import threading
import time

from newrelic_telemetry_sdk.metric import CountMetric, SummaryMetric


class MetricBatch(object):
    """Maps a metric identity to its aggregated value

    This is used to hold unfinalized metrics for further aggregation until they
    are flushed to a backend.

    :param tags: (optional) A dictionary of tags to attach to all flushes.
    :type tags: dict
    """

    LOCK_CLS = threading.Lock

    def __init__(self, tags=None):
        self._interval_start = int(time.time() * 1000.0)
        self._lock = self.LOCK_CLS()
        self._batch = {}
        tags = tags and dict(tags)
        self._common = {}
        if tags:
            self._common["attributes"] = tags

    @staticmethod
    def create_identity(metric):
        """Creates a deterministic hashable identity for a metric

        :param metric: A New Relic metric object
        :type metric: newrelic_telemetry_sdk.metric.Metric

        >>> from newrelic_telemetry_sdk import GaugeMetric
        >>> foo_0 = GaugeMetric('foo', 0, tags={'units': 'C'})
        >>> foo_1 = GaugeMetric('foo', 1, tags={'units': 'C'})
        >>> MetricBatch.create_identity(foo_0) == MetricBatch.create_identity(foo_1)
        True
        """
        tags = metric.tags
        if tags:
            tags = frozenset(tags.items())
        identity = (type(metric), metric.name, tags)
        return identity

    def record(self, item):
        """Merge a metric into the batch

        :param item: The metric to merge into the batch.
        :type item: newrelic_telemetry_sdk.metric.Metric
        """
        identity = self.create_identity(item)

        with self._lock:
            if identity in self._batch:
                merged = self._batch[identity]
                value = item["value"]

                if isinstance(item, SummaryMetric):
                    merged_value = merged["value"]
                    merged_value["count"] += value["count"]
                    merged_value["sum"] += value["sum"]
                    merged_value["min"] = min(value["min"], merged_value["min"])
                    merged_value["max"] = max(value["max"], merged_value["max"])
                elif isinstance(item, CountMetric):
                    merged["value"] += value
                else:
                    merged["value"] = value

            else:
                item = self._batch[identity] = item.copy()
                # Timestamp will now be tracked as part of the batch
                item.pop("timestamp")

    def flush(self):
        """Flush all metrics from the batch

        This method returns all metrics in the batch and a common block
        representing timestamp as the start time for the period since creation
        or last flush, and interval representing the total amount of time in
        milliseconds between flushes.

        As a side effect, the batch's interval is reset in anticipation of
        subsequent calls to flush.

        :returns: A tuple of (metrics, common)
        :rtype: tuple
        """
        with self._lock:
            batch = self._batch
            items = tuple(batch.values())
            batch.clear()

            common = self._common.copy()
            common["timestamp"] = self._interval_start
            now = int(time.time() * 1000.0)
            interval = now - self._interval_start
            common["interval.ms"] = interval

            self._interval_start = now

        return items, common
