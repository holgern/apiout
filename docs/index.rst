apiout Documentation
====================

**apiout** is a flexible Python tool for fetching data from APIs and serializing responses using TOML configuration files with powerful variable substitution and runtime parameter overrides.

Features
--------

* **Config-driven API calls**: Define API endpoints, parameters, and authentication in TOML files
* **Variable substitution**: Use ``${param_name}`` syntax for dynamic URLs and parameters with runtime overrides
* **Runtime parameter overrides**: Override defaults via CLI flags (``-p``), JSON stdin, or environment variables
* **Flexible serialization**: Map API responses to desired output formats using configurable field mappings
* **Reusable client configurations**: Define clients once and reference them from multiple APIs
* **Post-processors**: Combine and transform data from multiple API calls using Python classes
* **Separate concerns**: Keep API configurations and serializers in separate files for better organization
* **Default serialization**: Works without serializers - automatically converts objects to dictionaries
* **Generator tool**: Introspect API responses and auto-generate serializer configurations

Installation
------------

.. code-block:: bash

   pip install apiout

Quick Example
-------------

Create an API configuration file with variable substitution and default parameters:

.. code-block:: toml

   [[apis]]
   name = "weather"
   module = "openmeteo_requests"
   client_class = "Client"
   method = "weather_api"
   url = "https://api.open-meteo.com/v1/forecast"
   method_params = {latitude = 52.52, longitude = 13.41}

   [apis.params]
   latitude = "${latitude}"
   longitude = "${longitude}"
   current = ["temperature_2m"]

Run the API fetcher with runtime parameter override:

.. code-block:: bash

   # Override specific parameters
   apiout run --config config.toml -p latitude=48.8566 -p longitude=2.3522 --json

   # Or use JSON input
   echo '{"latitude": 51.5074, "longitude": -0.1278}' | apiout run --config config.toml --json

   # Or use environment variables as fallbacks
   export latitude=40.7128
   export longitude=-74.0060
   apiout run --config config.toml --json

Getting Started
---------------

* :doc:`quickstart` - Get up and running in minutes
* :doc:`user_guide` - Detailed configuration and usage guide
* :doc:`examples` - Practical examples and use cases
* :doc:`api_reference` - Programmatic API documentation

Key Concepts
------------

**Variable Substitution Priority:**

1. **Runtime parameters** (``-p`` flags or JSON stdin) - highest priority
2. **method_params defaults** - from configuration file  
3. **Environment variables** - fallback

**Understanding method_params vs [apis.params]:**

* ``method_params``: Default values for method arguments and variable substitution
* ``[apis.params]``: Actual parameters passed to the API method (can use variable substitution)

**Why do we need both?**

``method_params`` defines *default values* that can be overridden at runtime and used in variable substitution. ``[apis.params]`` defines the *actual parameters* sent to the API method.

**Example:**

.. code-block:: toml

   # Default values for substitution and method arguments
   method_params = {latitude = 52.52, longitude = 13.41, units = "metric"}
   
   # Actual API parameters (can use variables from method_params)
   [apis.params]
   latitude = "${latitude}"        # Uses runtime override or default
   longitude = "${longitude}"      # Uses runtime override or default  
   units = "${units}"             # Uses runtime override or default
   current = ["temperature_2m"]   # Static parameter

When you run ``apiout run -c config.toml -p latitude=48.8566``, the ``${latitude}`` in ``[apis.params]`` gets substituted with ``48.8566``, while ``longitude`` and ``units`` use their defaults from ``method_params``.

**Configuration Structure:**

* ``[[apis]]`` - Define API endpoints and methods
* ``[clients]`` - Reusable client configurations
* ``[serializers]`` - Response data transformation
* ``[[post_processors]]`` - Combine multiple API results

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
