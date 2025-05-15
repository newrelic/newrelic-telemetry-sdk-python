API Reference
=============

.. module:: newrelic_telemetry_sdk

New Relic HTTP Clients
----------------------
.. automodule:: newrelic_telemetry_sdk.client
    :members:
    :undoc-members:
    :inherited-members:
    :exclude-members: HOST, PATH, PAYLOAD_TYPE, HEADERS, GZIP_HEADER, Client, HTTPResponse


.. autoclass:: newrelic_telemetry_sdk.client.HTTPResponse()
    :members:

Metrics
-------
.. automodule:: newrelic_telemetry_sdk.metric
    :members:
    :undoc-members:
    :exclude-members: Metric

Events
-------
.. automodule:: newrelic_telemetry_sdk.event
    :members:

Logs
----
.. automodule:: newrelic_telemetry_sdk.log
    :members:

Spans
-----
.. automodule:: newrelic_telemetry_sdk.span
    :members:

Batches
-------
.. automodule:: newrelic_telemetry_sdk.metric_batch
    :members:
    :exclude-members: LOCK_CLS

.. automodule:: newrelic_telemetry_sdk.batch
    :members:
    :exclude-members: Batch, LOCK_CLS
    :inherited-members:

Harvester
---------
.. automodule:: newrelic_telemetry_sdk.harvester
    :members:
    :exclude-members: EVENT_CLS, run, daemon
    :show-inheritance:
    :inherited-members:
