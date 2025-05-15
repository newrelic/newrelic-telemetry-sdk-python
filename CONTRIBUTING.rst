Contributing to the Telemetry SDK
=================================

Thanks for your interest in contributing to the
``newrelic-telemetry-sdk-python``! We look forward to engaging with you.

How to Contribute
-----------------

-  Read this CONTRIBUTING file
-  Read our `Code of Conduct <CODE_OF_CONDUCT.md>`__
-  Submit a `pull request <#pull-request-guidelines>`__ or
   `issue <#filing-issues--bug-reports>`__. For pull requests, please
   also:

   -  Ensure the `test suite passes <#testing-guidelines>`__.
   -  Sign the `Contributor Licensing
      Agreement <#contributor-license-agreement-cla>`__, if you haven’t
      already done so. (You will be prompted if we don’t have a signed
      CLA already recorded.)

How to Get Help or Ask Questions
--------------------------------

Do you have questions or are you experiencing unexpected behaviors after
modifying this Open Source Software? Please engage with the “Build on
New Relic” space in the `Explorers
Hub <https://discuss.newrelic.com/c/build-on-new-relic/Open-Source-Agents-SDKs>`__,
New Relic’s Forum. Posts are publicly viewable by anyone, please do not
include PII or sensitive information in your forum post.

Contributor License Agreement (“CLA”)
-------------------------------------

We’d love to get your contributions to improve Telemetry SDK! Keep in
mind when you submit your pull request, you’ll need to sign the CLA via
the click-through using CLA-Assistant. You only have to sign the CLA one
time per project. To execute our corporate CLA, which is required if
your contribution is on behalf of a company, or if you have any
questions, please drop us an email at open-source@newrelic.com.

Filing Issues & Bug Reports
---------------------------

We use GitHub issues to track public issues and bugs. If possible,
please provide a link to an example app or gist that reproduces the
issue. When filing an issue, please ensure your description is clear and
includes the following information.

* Project version (ex: 1.4.0)
* Custom configurations (ex: flag=true)
* Any modifications made to the Telemetry SDK

A note about vulnerabilities
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

New Relic is committed to the security of our customers and their data.
We believe that providing coordinated disclosure by security researchers
and engaging with the security community are important means to achieve
our security goals.

If you believe you have found a security vulnerability in this project
or any of New Relic’s products or websites, we welcome and greatly
appreciate you reporting it to New Relic through
`our bug bounty program <https://docs.newrelic.com/docs/security/security-privacy/information-security/report-security-vulnerabilities/>`__.

Setting Up Your Environment
---------------------------

This Open Source Software can be used in a large number of environments,
all of which have their own quirks and best practices. As such, while we
are happy to provide documentation and assistance for unmodified Open
Source Software, we cannot provide support for your specific
environment.

Pull Request Guidelines
-----------------------

Before we can accept a pull request, you must sign our `Contributor
Licensing Agreement <#contributor-license-agreement-cla>`__, if you have
not already done so. This grants us the right to use your code under the
same Apache 2.0 license as we use for this project in general.

Minimally, the `test suite <#testing-guidelines>`__ must pass for us to
accept a PR. Ideally, we would love it if you also added appropriate
tests if you’re implementing a feature!

Coding Style Guidelines
-----------------------

Our code base is formatted and linted with
`ruff <https://github.com/astral-sh/ruff>`__

Testing Guidelines
------------------

The Telemetry SDK uses `tox <https://github.com/tox-dev/tox>`__ for
testing. The repository uses doctests in `src/ <src/>`__ and tests in
`tests/ <tests/>`__.

You can run all of these tests, and verify that your code is formatted
correctly by running:

``tox -e py``

``ruff format && ruff check --fix``

License
-------

By contributing to the Python Telemetry SDK, you agree that your
contributions will be licensed under the `License file <LICENSE>`__ in
the root directory of this source tree.
