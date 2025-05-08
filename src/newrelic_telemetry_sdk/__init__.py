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

from newrelic_telemetry_sdk.batch import EventBatch, SpanBatch
from newrelic_telemetry_sdk.client import EventClient, HTTPError, LogClient, MetricClient, SpanClient
from newrelic_telemetry_sdk.event import Event
from newrelic_telemetry_sdk.harvester import Harvester
from newrelic_telemetry_sdk.log import Log, NewRelicLogFormatter
from newrelic_telemetry_sdk.metric import CountMetric, GaugeMetric, SummaryMetric
from newrelic_telemetry_sdk.metric_batch import MetricBatch
from newrelic_telemetry_sdk.span import Span

try:
    from newrelic_telemetry_sdk.version import __version__, __version_tuple__
except ImportError:  # pragma: no cover
    __version__ = "unknown"  # pragma: no cover
    __version_tuple__ = (0, 0, 0, "unknown")  # pragma: no cover


__all__ = (
    "CountMetric",
    "Event",
    "EventBatch",
    "EventClient",
    "GaugeMetric",
    "HTTPError",
    "Harvester",
    "Log",
    "LogClient",
    "MetricBatch",
    "MetricClient",
    "NewRelicLogFormatter",
    "Span",
    "SpanBatch",
    "SpanClient",
    "SummaryMetric",
)
