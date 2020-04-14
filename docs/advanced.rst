Advanced Usage
==============

The telemetry SDK includes components to simplify data aggregation for long running applications.

Batches
-------

Batches provide a standard interface for aggregating and flushing data across different data types. This interface is used by the harvester to forward data from batches to a client.

Batches will automatically track the interval over which data is aggregated so you don't have to manually set ``interval_ms`` on metrics!

All public batch methods are thread safe.

Batches are broken out by data type that they contain:

+----------------------------------------------------------+---------------------------------------------------------------------------+
| Data Type                                                | Batch Type                                                                |
+==========================================================+===========================================================================+
| :class:`Metric <newrelic_telemetry_sdk.metric.Metric>`   | :class:`MetricBatch <newrelic_telemetry_sdk.metric_batch.MetricBatch>`    |
+----------------------------------------------------------+---------------------------------------------------------------------------+
| :class:`Event <newrelic_telemetry_sdk.span.Event>`       | :class:`EventBatch <newrelic_telemetry_sdk.batch.EventBatch>`             |
+----------------------------------------------------------+---------------------------------------------------------------------------+
| :class:`Span <newrelic_telemetry_sdk.span.Span>`         | :class:`SpanBatch <newrelic_telemetry_sdk.batch.SpanBatch>`               |
+----------------------------------------------------------+---------------------------------------------------------------------------+

Example
^^^^^^^

.. code-block:: python

    from newrelic_telemetry_sdk import CountMetric, MetricBatch

    metric_batch = MetricBatch()

    # Record that there have been 5 errors
    # Interval is not required since the metric will be placed in a batch!
    errors = CountMetric(name="errors", value=5)
    metric_batch.record(errors)

    # Calling flush will clear the batch and reset the interval start time
    items, common = metric_batch.flush()

    # The interval is automatically set by the batch!
    print(common["interval.ms"])

Harvester
---------

A :class:`Harvester <newrelic_telemetry_sdk.harvester.Harvester>` flushes a batch and sends data through a client at a fixed harvest interval.

The :class:`Harvester <newrelic_telemetry_sdk.harvester.Harvester>` class is a :class:`threading.Thread` and has :meth:`start <newrelic_telemetry_sdk.harvester.Harvester.start>` and :meth:`stop <newrelic_telemetry_sdk.harvester.Harvester.stop>` methods.

The :meth:`record <newrelic_telemetry_sdk.harvester.Harvester.record>` method intentionally has the same signature as a batch's record method. For all intents and purposes, the harvester can be treated as a batch that will be periodically flushed and sent to New Relic.

Example
^^^^^^^
The example code assumes you've set the following environment variables:

* ``NEW_RELIC_INSERT_KEY``

.. code-block:: python

    import atexit
    import os
    from newrelic_telemetry_sdk import GaugeMetric, MetricBatch, MetricClient, Harvester

    metric_client = MetricClient(os.environ['NEW_RELIC_INSERT_KEY'])
    metric_batch = MetricBatch()
    metric_harvester = Harvester(metric_client, metric_batch)

    # Send any buffered data when the process exits
    atexit.register(metric_harvester.stop)

    # Start the harvester background thread
    metric_harvester.start()

    # Data is now recorded through the harvester
    # The data will buffer and send every 5 seconds or at process exit
    temperature = GaugeMetric("temperature", 78.6, {"units": "Farenheit"})
    metric_harvester.record(temperature)
