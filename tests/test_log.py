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

import json
import logging
import os
import sys
import threading

import pytest

from newrelic_telemetry_sdk import Log, NewRelicLogFormatter


class MyError(Exception):
    pass


BASE_RECORD_DICT = {"name": "test_record", "levelname": "WARNING", "pathname": "/", "lineno": 12, "msg": "message"}


@pytest.mark.parametrize("extras", ({}, {"extra": "a little bit"}))
def test_log_extract_data(extras):
    record_dict = BASE_RECORD_DICT.copy()
    record_dict.update(extras)
    record = logging.makeLogRecord(record_dict)
    output = Log.extract_record_data(record)
    current_thread = threading.current_thread()
    expected_output = {
        "timestamp": int(record.created * 1000),
        "message": "message",
        "log.level": "WARNING",
        "logger.name": "test_record",
        "thread.id": current_thread.ident,
        "thread.name": current_thread.name,
        "process.id": os.getpid(),
        "process.name": "MainProcess",
        "file.name": "/",
        "line.number": 12,
    }
    expected_output.update(extras)
    assert output == expected_output


@pytest.mark.parametrize("error_cls", (ValueError, MyError))
def test_log_extract_data_exception(error_cls):
    try:
        raise error_cls("uh oh")
    except Exception:
        exc_info = sys.exc_info()
    record = logging.makeLogRecord({"exc_info": exc_info})

    # Log is instantiated here to ensure a staticmethod is used
    output = Log("").extract_record_data(record)

    cls_name = f"{error_cls.__module__}.{error_cls.__name__}"

    assert output["error.class"] == cls_name
    assert output["error.message"] == "uh oh"
    assert 'raise error_cls("uh oh")\n' in output["error.stack"]


@pytest.mark.parametrize("attributes", ({}, {"foo": "bar"}))
def test_log_creation(attributes):
    log = Log("message", timestamp=1, **attributes)
    expected = {"timestamp": 1, "message": "message"}
    if attributes:
        expected["attributes"] = attributes
    assert dict(log) == expected


def test_log_default_timestamp(freeze_time):
    log = Log("message")
    assert dict(log) == {"message": "message", "timestamp": 2000}


def test_log_from_log_record():
    record = logging.makeLogRecord(
        {
            "name": "test_record",
            "levelname": "WARNING",
            "pathname": "/",
            "lineno": 12,
            "msg": "Logger exception",
            "extra_str": "str",
            "extra_int": 9000,
            "extra_float": 1.23,
            "extra_bool": True,
            "extra_dict": {},
            "extra_tuple": (),
            "extra_list": [],
        }
    )
    log = Log.from_record(record)

    current_thread = threading.current_thread()
    assert dict(log) == {
        "timestamp": int(record.created * 1000),
        "message": "Logger exception",
        "attributes": {
            "log.level": "WARNING",
            "logger.name": "test_record",
            "thread.id": current_thread.ident,
            "thread.name": current_thread.name,
            "process.id": os.getpid(),
            "process.name": "MainProcess",
            "file.name": "/",
            "line.number": 12,
            "extra_str": "str",
            "extra_int": 9000,
            "extra_float": 1.23,
            "extra_bool": True,
            "extra_dict": "{}",
            "extra_tuple": "()",
            "extra_list": "[]",
        },
    }


@pytest.mark.parametrize("extras", ({}, {"extra": "yes"}))
def test_log_format(extras):
    # Verify specifying arguments do not crash
    formatter = NewRelicLogFormatter("%(message)s", datefmt="%Y")
    record_dict = BASE_RECORD_DICT.copy()
    record_dict.update(extras)
    record = logging.makeLogRecord(record_dict)
    output = formatter.format(record)

    # Verify all spaces have been removed
    assert " " not in output

    # Output is valid JSON
    current_thread = threading.current_thread()
    expected_output = {
        "timestamp": int(record.created * 1000),
        "message": "message",
        "log.level": "WARNING",
        "logger.name": "test_record",
        "thread.id": current_thread.ident,
        "thread.name": current_thread.name,
        "process.id": os.getpid(),
        "process.name": "MainProcess",
        "file.name": "/",
        "line.number": 12,
    }
    expected_output.update(extras)
    assert json.loads(output) == expected_output
