# Copyright 2020 New Relic, Inc.
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
from newrelic_telemetry_sdk.span_batch import SpanBatch


@pytest.mark.parametrize("tags", (None, {"foo": "bar"},))
def test_span_batch_common_tags(tags):
    batch = SpanBatch(tags)

    if tags:
        expected = {"attributes": tags}
    else:
        expected = None

    _, common = batch.flush()
    assert common == expected

    if expected:
        # Verify that we don't return the same objects twice
        assert batch.flush()[1] is not common


def test_span_batch_simple():
    batch = SpanBatch()

    # Verify that item is recorded and that flush clears out the batch
    for _ in range(2):
        item = object()
        batch.record(item)

        assert batch.flush()[0] == (item,)
