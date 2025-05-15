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
import time
import traceback

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

DEFAULT_LOG_RECORD_KEYS = frozenset(vars(logging.makeLogRecord({})))


class Log(dict):
    """A log representing a log event in the New Relic logging UI

    This data structure represents a single log event. These objects, when JSON
    serialized, can be sent to New Relic's log api.

    :param message: The log message.
    :type message: str
    :param timestamp: (optional) The unix timestamp in milliseconds indicating
        when the log message was generated. Defaults to now.
    :type timestamp:
    :param \\**attributes: Additional attribute name=value pairs provided as keyword
        arguments.
    """

    def __init__(self, message, timestamp=None, **attributes):
        self["message"] = message
        self["timestamp"] = int(timestamp or (time.time() * 1000))
        if attributes:
            self["attributes"] = attributes

    @staticmethod
    def extract_record_data(record):
        """Extracts data from a logging.LogRecord into a flat dictionary

        :param record: The LogRecord from which to extract data.
        :type record: logging.LogRecord

        >>> import logging
        >>> record = logging.makeLogRecord({"msg": "Hello World"})
        >>> result = Log.extract_record_data(record)
        >>> isinstance(result, dict)
        True
        >>> result["message"]
        'Hello World'

        :rtype: dict
        """
        output = {
            "timestamp": int(record.created * 1000),
            "message": record.getMessage(),
            "log.level": record.levelname,
            "logger.name": record.name,
            "thread.id": record.thread,
            "thread.name": record.threadName,
            "process.id": record.process,
            "process.name": record.processName,
            "file.name": record.pathname,
            "line.number": record.lineno,
        }

        if len(record.__dict__) > len(DEFAULT_LOG_RECORD_KEYS):
            default_keys = DEFAULT_LOG_RECORD_KEYS
            for key in record.__dict__:
                if key not in default_keys:
                    value = getattr(record, key)
                    if not isinstance(value, (str, int, float, bool)) and value is not None:
                        value = str(value)
                    output[key] = value

        if record.exc_info:
            error_cls, error_value, error_tb = record.exc_info
            output["error.class"] = getattr(error_cls, "__module__", "builtins") + "." + error_cls.__name__
            output["error.message"] = str(error_value)
            s = StringIO()
            traceback.print_exception(error_cls, error_value, error_tb, None, s)
            output["error.stack"] = s.getvalue().rstrip()
            s.close()

        return output

    @classmethod
    def from_record(cls, record):
        """Convert a logging.LogRecord into a Log

        This converts a :py:class:`logging.LogRecord` to a New Relic
        :py:class:`Log`, extracting any dimensions/labels from the record.

        :param record: The LogRecord to convert.
        :type record: logging.LogRecord

        >>> import logging
        >>> record = logging.makeLogRecord({"msg": "Hello World"})
        >>> log = Log.from_record(record)
        >>> log["message"]
        'Hello World'
        """
        return cls(**cls.extract_record_data(record))


class NewRelicLogFormatter(logging.Formatter):
    """New Relic Log Formatter

    The New Relic log formatter converts LogRecord instances to strings via the
    format method.

    The New Relic log format allows for arbitrary key/value pairs to be logged.
    This formatter automatically extracts all relevant information from the
    LogRecord (including extras) and places those key/values into a JSON
    object.

    Since the format is not configurable, all formatter constructor arguments
    are ignored.

    Usage::

        >>> import logging
        >>> record = logging.makeLogRecord({})
        >>> formatter = NewRelicLogFormatter()
        >>> result = formatter.format(record)
        >>> isinstance(result, str)
        True
    """

    def __init__(self, *args, **kwargs):  # noqa: ARG002
        super().__init__()

    def format(self, record):
        """Format the specified record as text

        :param record: The LogRecord to format.
        :type record: logging.LogRecord

        :rtype: str
        """
        return json.dumps(Log.extract_record_data(record), separators=(",", ":"))
