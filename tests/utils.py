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


class CustomMapping:
    def __getitem__(self, key):
        if key == "foo":
            return "bar"
        raise KeyError(key)

    def __iter__(self):
        return iter(("foo",))

    def __len__(self):
        return 1

    def keys(self):
        return ("foo",)
