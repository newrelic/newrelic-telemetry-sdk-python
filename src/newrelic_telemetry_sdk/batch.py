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


class Batch:
    """Implements aggregation, providing a record / flush interface.

    :param tags: (optional) A dictionary of tags to attach to all flushes.
    :type tags: dict
    """

    LOCK_CLS = threading.Lock

    def __init__(self, tags=None):
        self._lock = self.LOCK_CLS()
        self._batch = []
        tags = tags and dict(tags)
        if tags:
            self._common = {"attributes": tags}
        else:
            self._common = None

    def record(self, item):
        """Merge an item into the batch

        :param item: The item to merge into the batch.
        """
        with self._lock:
            self._batch.append(item)

    def flush(self):
        """Flush all items from the batch

        This method returns all items in the batch and a common block
        representing any tags if applicable.

        The batch is cleared as part of this operation.

        :returns: A tuple of (items, common)
        :rtype: tuple
        """
        with self._lock:
            batch = tuple(self._batch)
            self._batch[:] = []

        common = self._common and self._common.copy()
        return batch, common


class SpanBatch(Batch):
    """Aggregates spans, providing a record / flush interface.

    :param tags: (optional) A dictionary of tags to attach to all flushes.
    :type tags: dict
    """


class LogBatch(Batch):
    """Aggregates logs, providing a record / flush interface.

    :param tags: (optional) A dictionary of tags to attach to all flushes.
    :type tags: dict
    """


class EventBatch(Batch):
    """Aggregates events, providing a record / flush interface."""

    def __init__(self):
        super().__init__()

    def flush(self):
        """Flush all items from the batch

        This method returns all items in the batch.

        The batch is cleared as part of this operation.

        :returns: A tuple of (items,)
        :rtype: tuple
        """
        items, _ = super().flush()
        return (items,)
