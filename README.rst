|header|

.. |header| image:: https://github.com/newrelic/open-source-office/raw/master/examples/categories/images/Community_Project.png
    :target: https://github.com/newrelic/open-source-office/blob/master/examples/categories/index.md#category-community-project

New Relic Telemetry SDK
=======================

|ci| |coverage| |docs| |ruff|

.. |ci| image:: https://github.com/newrelic/newrelic-telemetry-sdk-python/workflows/Tests/badge.svg
    :target: https://github.com/newrelic/newrelic-telemetry-sdk-python/actions?query=workflow%3ATests

.. |coverage| image:: https://img.shields.io/codecov/c/github/newrelic/newrelic-telemetry-sdk-python/main
    :target: https://codecov.io/gh/newrelic/newrelic-telemetry-sdk-python

.. |docs| image:: https://img.shields.io/badge/docs-available-brightgreen.svg
    :target: https://newrelic.github.io/newrelic-telemetry-sdk-python/

.. |ruff| image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v0.json
    :target: https://github.com/astral-sh/ruff

`newrelic-telemetry-sdk-python <https://docs.newrelic.com/docs/data-ingest-apis/get-data-new-relic/new-relic-sdks/telemetry-sdks-send-custom-telemetry-data-new-relic>`_ provides a Python library for sending data into `New Relic <https://newrelic.com>`_ using the Python `urllib3 <https://urllib3.readthedocs.io>`_ library.

See dimensional `metrics`_, `events`_, `logs`_, and `spans/traces`_ in New Relic, without having to use an agent!

.. _metrics: https://docs.newrelic.com/docs/data-ingest-apis/get-data-new-relic/metric-api/introduction-metric-api#find-data
.. _events: https://docs.newrelic.com/docs/insights/insights-data-sources/custom-data/introduction-event-api#find-data
.. _logs: https://docs.newrelic.com/docs/logs/log-management/ui-data/explore-your-data-log-analytics
.. _spans/traces: https://docs.newrelic.com/docs/understand-dependencies/distributed-tracing/trace-api/introduction-trace-api#view-data


Installing newrelic_telemetry_sdk
---------------------------------

To start, the ``newrelic-telemetry-sdk`` package must be installed. To install
through pip:

.. code-block:: bash

    $ pip install newrelic-telemetry-sdk

If that fails, download the library from its GitHub page and install it using:

.. code-block:: bash

    $ python setup.py install


Reporting your first metric
---------------------------

There are 3 different types of metrics:

* GaugeMetric
* CountMetric
* SummaryMetric

Metric descriptions
^^^^^^^^^^^^^^^^^^^

+-------------+----------+----------------------------------------------------+-----------------------------------------------+
| Metric type | Interval | Description                                        | Example                                       |
|             | required |                                                    |                                               |
+=============+==========+====================================================+===============================================+
| Gauge       | No       | A single value at a single point in time.          | Room Temperature.                             |
+-------------+----------+----------------------------------------------------+-----------------------------------------------+
| Count       | Yes      | Track the total number of occurrences of an event. | Number of errors that have occurred.          |
+-------------+----------+----------------------------------------------------+-----------------------------------------------+
| Summary     | Yes      | Track count, sum, min, and max values over time.   | The summarized duration of 100 HTTP requests. |
+-------------+----------+----------------------------------------------------+-----------------------------------------------+

Example
^^^^^^^
The example code assumes you've set the following environment variables:

* ``NEW_RELIC_LICENSE_KEY``

.. code-block:: python

    import os
    import time
    from newrelic_telemetry_sdk import GaugeMetric, CountMetric, SummaryMetric, MetricClient

    metric_client = MetricClient(os.environ["NEW_RELIC_LICENSE_KEY"])

    temperature = GaugeMetric("temperature", 78.6, {"units": "Farenheit"})

    # Record that there have been 5 errors in the last 2 seconds
    errors = CountMetric(name="errors", value=5, interval_ms=2000)

    # Record a summary of 10 response times over the last 2 seconds
    summary = SummaryMetric(
        "responses", count=10, min=0.2, max=0.5, sum=4.7, interval_ms=2000
    )

    batch = [temperature, errors, summary]
    response = metric_client.send_batch(batch)
    response.raise_for_status()
    print("Sent metrics successfully!")

Reporting your first event
--------------------------

Events represent a record of something that has occurred on a system being monitored.
The example code assumes you've set the following environment variables:

* ``NEW_RELIC_LICENSE_KEY``

.. code-block:: python

    import os
    import time
    from newrelic_telemetry_sdk import Event, EventClient

    # Record that a rate limit has been applied to an endpoint for an account
    event = Event(
        "RateLimit", {"path": "/v1/endpoint", "accountId": 1000, "rejectRatio": 0.1}
    )

    event_client = EventClient(os.environ["NEW_RELIC_LICENSE_KEY"])
    response = event_client.send(event)
    response.raise_for_status()
    print("Event sent successfully!")

Reporting your first log message
--------------------------------

Log messages are generated by applications, usually via the Python logging
module. These messages are used to audit and diagnose issues with an operating
application. The example code assumes you've set the following environment variables:

* ``NEW_RELIC_LICENSE_KEY``

.. code-block:: python

    import os

    from newrelic_telemetry_sdk import Log, LogClient

    log = Log("Hello World!")

    log_client = LogClient(os.environ["NEW_RELIC_LICENSE_KEY"])
    response = log_client.send(log)
    response.raise_for_status()
    print("Log sent successfully!")


Reporting your first span
-------------------------

Spans provide an easy way to time components of your code.
The example code assumes you've set the following environment variables:

* ``NEW_RELIC_LICENSE_KEY``

.. code-block:: python

    import os
    import time
    from newrelic_telemetry_sdk import Span, SpanClient

    with Span(name="sleep") as span:
        time.sleep(0.5)

    span_client = SpanClient(os.environ["NEW_RELIC_LICENSE_KEY"])
    response = span_client.send(span)
    response.raise_for_status()
    print("Span sleep sent successfully!")

Find and use data
-----------------

Tips on how to find and query your data in New Relic:

* `Find metric data <https://docs.newrelic.com/docs/data-ingest-apis/get-data-new-relic/metric-api/introduction-metric-api#find-data>`_
* `Find event data <https://docs.newrelic.com/docs/insights/insights-data-sources/custom-data/introduction-event-api#find-data>`_
* `Find log data <https://docs.newrelic.com/docs/logs/log-management/ui-data/explore-your-data-log-analytics>`_
* `Find trace/span data <https://docs.newrelic.com/docs/understand-dependencies/distributed-tracing/trace-api/introduction-trace-api#view-data>`_

For general querying information, see:

* `Query New Relic data <https://docs.newrelic.com/docs/using-new-relic/data/understand-data/query-new-relic-data>`_
* `Intro to NRQL <https://docs.newrelic.com/docs/query-data/nrql-new-relic-query-language/getting-started/introduction-nrql>`_

Limitations
-----------
The New Relic Telemetry APIs are rate limited. Please reference the documentation for `New Relic Metrics API <https://docs.newrelic.com/docs/introduction-new-relic-metric-api>`_ and `New Relic Trace API requirements and limits <https://docs.newrelic.com/docs/apm/distributed-tracing/trace-api/trace-api-general-requirements-limits>`_ on the specifics of the rate limits.

