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


class Event(dict):
    """An event represented in New Relic Insights

    :param event_type: The type of event to report
    :type event_type: str
    :param tags: (optional) A set of tags that can be used to filter this
        event in the New Relic UI.
    :type tags: dict
    :param timestamp_ms: (optional) A unix timestamp in milliseconds
        representing the timestamp in ms at which the event occurred. Defaults to
        time.time() * 1000
    :type timestamp_ms: int
    """

    def __init__(self, event_type, tags=None, timestamp_ms=None):
        timestamp = int(timestamp_ms or (time.time() * 1000))
        if tags:
            self.update(tags)
        super().__init__(eventType=event_type, timestamp=timestamp)

    def copy(self):
        cls = type(self)
        d = cls.__new__(cls)
        d.update(self)
        return d

    @property
    def event_type(self):
        """Event Type"""
        return self["eventType"]

    @property
    def timestamp_ms(self):
        """Event Timestamp"""
        return self["timestamp"]
