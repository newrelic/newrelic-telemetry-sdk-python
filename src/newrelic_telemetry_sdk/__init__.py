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

from newrelic_telemetry_sdk.client import SpanClient, MetricClient, HTTPError
from newrelic_telemetry_sdk.span import Span
from newrelic_telemetry_sdk.metric import GaugeMetric, CountMetric, SummaryMetric

try:
    from newrelic_telemetry_sdk.version import version as __version__
except ImportError:  # pragma: no cover
    __version__ = "unknown"  # pragma: no cover

__all__ = (
    "HTTPError",
    "SpanClient",
    "MetricClient",
    "Span",
    "GaugeMetric",
    "CountMetric",
    "SummaryMetric",
)
