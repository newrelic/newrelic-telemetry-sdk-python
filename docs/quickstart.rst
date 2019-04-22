Quickstart
==========

Installing newrelic_telemetry_sdk
---------------------------------

To start, the ``newrelic_telemetry_sdk`` package must be installed. To install
through pip:

.. code-block:: bash

    $ pip install newrelic-telemetry-sdk

If that fails, download the library from its GitHub page and install it using:

.. code-block:: bash

    $ python setup.py install


Reporting Your First Span
-------------------------

Spans provide an easy way to time components of your code.
The example code assumes you've set the following environment variables:

* ``NEW_RELIC_INSERT_KEY``

.. code-block:: python

    import os
    import time
    from newrelic_telemetry_sdk import Span, SpanClient

    with Span(name='sleep') as span:
        time.sleep(0.5)

    span_client = SpanClient(os.environ['NEW_RELIC_INSERT_KEY'])
    response = span_client.send(span)
    response.raise_for_status()
    print('Span sleep sent successfully!')

Reporting Your First Metric
---------------------------

There are 3 different types of metrics:

* :class:`GaugeMetric <newrelic_telemetry_sdk.metric.GaugeMetric>`
* :class:`CountMetric <newrelic_telemetry_sdk.metric.CountMetric>`
* :class:`SummaryMetric <newrelic_telemetry_sdk.metric.SummaryMetric>`

Metric Descriptions
^^^^^^^^^^^^^^^^^^^

+-------------+----------+----------------------------------------------------+-----------------------------------------------+
| Metric Type | Interval | Description                                        | Example                                       |
|             | Required |                                                    |                                               |
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

* ``NEW_RELIC_INSERT_KEY``

.. code-block:: python

    import os
    import time
    from newrelic_telemetry_sdk import GaugeMetric, CountMetric, SummaryMetric, MetricClient

    metric_client = MetricClient(os.environ['NEW_RELIC_INSERT_KEY'])

    temperature = GaugeMetric("temperature", 78.6, {"units": "Farenheit"})

    # Record that there have been 5 errors in the last 2 seconds
    errors = CountMetric(name="errors", value=5, interval_ms=2000)

    # Record a summary of 10 response times over the last 2 seconds
    summary = SummaryMetric(
        "responses", count=10, min=0.2, max=0.5, sum=4.7, interval_ms=2000
    )

    response = metric_client.send_batch((temperature, errors, summary))
    response.raise_for_status()
    print("Sent metrics successfully!")
