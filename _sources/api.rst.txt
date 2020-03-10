API Reference
=============

.. module:: newrelic_telemetry_sdk

New Relic HTTP Clients
----------------------
.. automodule:: newrelic_telemetry_sdk.client
    :members:
    :undoc-members:
    :inherited-members:
    :exclude-members: URL, HOST, PAYLOAD_TYPE, HEADERS, GZIP_HEADER, Client, HTTPResponse


.. autoclass:: newrelic_telemetry_sdk.client.HTTPResponse()
    :members:

Spans
-----
.. automodule:: newrelic_telemetry_sdk.span
    :members:

Metrics
-------
.. automodule:: newrelic_telemetry_sdk.metric
    :members:
    :undoc-members:
    :show-inheritance:


Batches
-------
.. automodule:: newrelic_telemetry_sdk.metric_batch
    :members:

.. automodule:: newrelic_telemetry_sdk.span_batch
    :members:

Harvester
---------
.. automodule:: newrelic_telemetry_sdk.harvester
    :members:
    :exclude-members: LOCK_CLS, EVENT_CLS, run, daemon
    :show-inheritance:
    :inherited-members:
