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
| :class:`Event <newrelic_telemetry_sdk.event.Event>`      | :class:`EventBatch <newrelic_telemetry_sdk.batch.EventBatch>`             |
+----------------------------------------------------------+---------------------------------------------------------------------------+
| :class:`Log <newrelic_telemetry_sdk.log.Log>`            | :class:`LogBatch <newrelic_telemetry_sdk.batch.LogBatch>`                 |
+----------------------------------------------------------+---------------------------------------------------------------------------+
| :class:`Span <newrelic_telemetry_sdk.span.Span>`         | :class:`SpanBatch <newrelic_telemetry_sdk.batch.SpanBatch>`               |
+----------------------------------------------------------+---------------------------------------------------------------------------+

Example
^^^^^^^

.. code-block:: python

    from newrelic_telemetry_sdk import CountMetric, MetricBatch

    metric_batch = MetricBatch()

    # Record that there have been 5 errors
    metric_batch.record_count("errors", 5)

    # Calling flush will clear the batch and reset the interval start time
    items, common = metric_batch.flush()

    # The interval is automatically set by the batch!
    print(common["interval.ms"])

Common fields
-------------

``SpanClient.send_batch``, ``MetricClient.send_batch``, and
``LogClient.send_batch`` accept an optional ``common`` dictionary. Its keys
use the same wire format as the telemetry items being sent, with all fields
optional. It is not a flat dictionary of tags: put shared tags inside the
``attributes`` key.

For example, spans can share a trace ID and service name:

.. code-block:: python

    import os
    from newrelic_telemetry_sdk import SpanClient

    client = SpanClient(os.environ["NEW_RELIC_LICENSE_KEY"])
    spans = [{
        "id": "0123456789abcdef",
        "timestamp": 1700000000000,
        "attributes": {"name": "example", "duration.ms": 10},
    }]
    common = {
        "trace.id": "0123456789abcdef0123456789abcdef",
        "attributes": {"service.name": "example-service"},
    }
    response = client.send_batch(spans, common=common)
    response.raise_for_status()

The example uses a fixed timestamp for illustration; use the actual span
start time when sending telemetry. A plain dictionary avoids generating
per-span IDs or timestamps for the shared block. ``SpanBatch(tags=...)`` and
``LogBatch(tags=...)`` create the nested ``attributes`` block for you when
flushed; ``MetricBatch`` also supplies the aggregation interval.
``EventClient.send_batch`` does not accept ``common``.

Harvester
---------

A :class:`Harvester <newrelic_telemetry_sdk.harvester.Harvester>` flushes a batch and sends data through a client at a fixed harvest interval.

The :class:`Harvester <newrelic_telemetry_sdk.harvester.Harvester>` class is a :class:`threading.Thread` and has :meth:`start <newrelic_telemetry_sdk.harvester.Harvester.start>` and :meth:`stop <newrelic_telemetry_sdk.harvester.Harvester.stop>` methods.

Example
^^^^^^^
The example code assumes you've set the following environment variables:

* ``NEW_RELIC_LICENSE_KEY``

.. code-block:: python

    import atexit
    import os
    from newrelic_telemetry_sdk import GaugeMetric, MetricBatch, MetricClient, Harvester

    metric_client = MetricClient(os.environ['NEW_RELIC_LICENSE_KEY'])
    metric_batch = MetricBatch()
    metric_harvester = Harvester(metric_client, metric_batch)

    # Send any buffered data when the process exits
    atexit.register(metric_harvester.stop)

    # Start the harvester background thread
    metric_harvester.start()

    # The data will buffer and send every 5 seconds or at process exit
    metric_batch.record_gauge("temperature", 78.6, {"units": "Farenheit"})
