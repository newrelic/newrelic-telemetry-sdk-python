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
from utils import CustomMapping

from newrelic_telemetry_sdk.batch import Batch, EventBatch


class VerifyLockBatch(Batch):
    """Verify sensitive attributes are accessed / assigned under lock

    These attributes are sensitive and should only be accessed under lock.
    NOTE: It doesn't guarantee that the values returned are only modified under
    lock; however, this provides some level of checking.
    """

    @property
    def _batch(self):
        assert self._lock.locked()
        return self._internal_batch

    @_batch.setter
    def _batch(self, value):
        if hasattr(self, "_internal_batch"):
            assert self._lock.locked()
        self._internal_batch = value

    @property
    def _common(self):
        return self._internal_common

    @_common.setter
    def _common(self, value):
        # This attribute should never be assigned
        assert not hasattr(self, "_internal_common")
        self._internal_common = value


@pytest.mark.parametrize("tags", (None, {"foo": "bar"}, CustomMapping()))
def test_batch_common_tags(tags):
    batch = VerifyLockBatch(tags)

    expected = {"attributes": dict(tags)} if tags else None

    _, common = batch.flush()
    assert common == expected

    if expected:
        # Verify that we don't return the same objects twice
        assert batch.flush()[1] is not common


@pytest.mark.parametrize("batch_cls", (VerifyLockBatch, EventBatch))
def test_batch_simple(batch_cls):
    batch = batch_cls()

    # Verify that item is recorded and that flush clears out the batch
    for _ in range(2):
        item = object()
        batch.record(item)

        assert batch.flush()[0] == (item,)
