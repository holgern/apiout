apiout Documentation
===================

**apiout** is a flexible Python tool for fetching data from APIs and serializing responses using TOML configuration files.

Features
--------

* **Config-driven API calls**: Define API endpoints, parameters, and authentication in TOML files
* **Flexible serialization**: Map API responses to desired output formats using configurable field mappings
* **Separate concerns**: Keep API configurations and serializers in separate files for better organization
* **Default serialization**: Works without serializers - automatically converts objects to dictionaries
* **Generator tool**: Introspect API responses and auto-generate serializer configurations

Installation
------------

.. code-block:: bash

   pip install apiout

Quick Example
-------------

Create an API configuration file:

.. code-block:: toml

   [[apis]]
   name = "weather"
   module = "openmeteo_requests"
   client_class = "Client"
   method = "weather_api"
   url = "https://api.open-meteo.com/v1/forecast"

   [apis.params]
   latitude = 52.52
   longitude = 13.41
   current = ["temperature_2m"]

Run the API fetcher:

.. code-block:: bash

   apiout run -c config.toml --json

Contents
--------

.. toctree::
   :maxdepth: 2

   quickstart
   user_guide
   examples
   api_reference

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
