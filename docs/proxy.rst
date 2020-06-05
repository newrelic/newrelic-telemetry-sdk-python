Proxy Support
=============

The telemetry SDK includes support for HTTP proxies via environment variables and on MacOS / Windows via operating system registry as described in the Python `getproxies <https://docs.python.org/3/library/urllib.request.html#urllib.request.getproxies>`_ documentation.


HTTP Proxy
----------

The telemetry SDK only supports HTTPS over HTTP proxies. Therefore, the proxy must be configured using the ``https_proxy`` environment variable and the configured URL must have the scheme ``http``.

Example
^^^^^^^

.. code-block:: bash

   export https_proxy="http://myproxy.localhost:3128"


Authenticated HTTP Proxy
------------------------

The telemetry SDK supports proxy credentials sent over `basic auth <https://tools.ietf.org/html/rfc7617>`_. To use proxy authentication, the credentials should be specified in the ``https_proxy`` environment variable URL.

.. DANGER::

   Proxy credentials are sent in plaintext via an HTTP header. Any attacker with access to the network transporting the proxy credentials will be able to observe the proxy credentials. New Relic credentials are never sent in plaintext.

Example
^^^^^^^

.. code-block:: bash

   export https_proxy="http://username:password@myproxy.localhost:3128"
