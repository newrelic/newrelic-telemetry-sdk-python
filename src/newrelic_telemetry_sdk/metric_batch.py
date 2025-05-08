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


class MetricBatch:
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
        self._timestamps = {}
        tags = tags and dict(tags)
        self._common = {}
        if tags:
            self._common["attributes"] = tags

    @staticmethod
    def create_identity(name, tags=None, typ=None):
        """Creates a deterministic hashable identity for a metric

        :param name: The name of the metric.
        :type name: str
        :param tags: (optional) A set of tags that can be used to
            filter this metric in the New Relic UI.
        :type tags: dict
        :param typ: (optional) The metric type. One of "summary", "count",
            "gauge" or None. Default: None (gauge type).
        :type typ: str
        """
        if tags:
            tags = frozenset(tags.items())
        return (typ, name, tags)

    def record_gauge(self, name, value, tags=None):
        """Records a gauge metric

        :param name: The name of the metric.
        :type name: str
        :param value: The metric value.
        :type value: int or float
        :param tags: (optional) A set of tags that can be used to
            filter this metric in the New Relic UI.
        :type tags: dict
        """
        identity = self.create_identity(name, tags)
        with self._lock:
            self._batch[identity] = value
            self._timestamps[identity] = int(time.time() * 1000.0)

    def record_count(self, name, value, tags=None):
        """Records a count metric

        :param name: The name of the metric.
        :type name: str
        :param value: The metric value.
        :type value: int or float
        :param tags: (optional) A set of tags that can be used to
            filter this metric in the New Relic UI.
        :type tags: dict
        """
        identity = self.create_identity(name, tags, "count")
        with self._lock:
            self._batch[identity] = self._batch.get(identity, 0) + value

    def record_summary(self, name, value, tags=None):
        """Records a summary metric

        :param name: The name of the metric.
        :type name: str
        :param value: The metric value.
        :type value: int or float
        :param tags: (optional) A set of tags that can be used to
            filter this metric in the New Relic UI.
        :type tags: dict
        """
        identity = self.create_identity(name, tags, "summary")
        with self._lock:
            if identity in self._batch:
                merged_value = self._batch[identity]
                merged_value["count"] += 1
                merged_value["sum"] += value
                merged_value["min"] = min(value, merged_value["min"])
                merged_value["max"] = max(value, merged_value["max"])
            else:
                value = {"count": 1, "sum": value, "min": value, "max": value}
                self._batch[identity] = value

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
            timestamps = self._timestamps

            items = []
            for identity, value in batch.items():
                metric = {}
                typ, name, tags = identity
                metric["name"] = name
                if typ:
                    metric["type"] = typ
                else:
                    metric["timestamp"] = timestamps[identity]

                if tags:
                    metric["attributes"] = dict(tags)

                metric["value"] = value
                items.append(metric)

            items = tuple(items)

            batch.clear()
            timestamps.clear()

            common = self._common.copy()
            common["timestamp"] = self._interval_start
            now = int(time.time() * 1000.0)
            interval = now - self._interval_start
            common["interval.ms"] = interval

            self._interval_start = now

        return items, common
