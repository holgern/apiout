API Reference
=============

This page provides detailed API documentation for using **apiout** programmatically.

Modules
-------

apiout.cli
~~~~~~~~~~

.. automodule:: apiout.cli
   :members:
   :undoc-members:
   :show-inheritance:

apiout.fetcher
~~~~~~~~~~~~~~

.. automodule:: apiout.fetcher
   :members:
   :undoc-members:
   :show-inheritance:

apiout.serializer
~~~~~~~~~~~~~~~~~

.. automodule:: apiout.serializer
   :members:
   :undoc-members:
   :show-inheritance:

apiout.generator
~~~~~~~~~~~~~~~~

.. automodule:: apiout.generator
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

fetch_api_data
~~~~~~~~~~~~~~

.. autofunction:: apiout.fetcher.fetch_api_data

Fetches data from an API using the provided configuration.

**Parameters:**

* ``api_config`` (Dict[str, Any]): API configuration dictionary
* ``global_serializers`` (Optional[Dict[str, Any]]): Global serializer configurations

**Returns:**

* ``Any``: Serialized API response or error dictionary

**Example:**

.. code-block:: python

   from apiout.fetcher import fetch_api_data

   config = {
       "name": "test",
       "module": "requests",
       "client_class": "Session",
       "method": "get",
       "url": "https://api.example.com",
       "params": {}
   }

   result = fetch_api_data(config)

resolve_serializer
~~~~~~~~~~~~~~~~~~

.. autofunction:: apiout.fetcher.resolve_serializer

Resolves serializer configuration from API config and global serializers.

**Parameters:**

* ``api_config`` (Dict[str, Any]): API configuration dictionary
* ``global_serializers`` (Optional[Dict[str, Any]]): Global serializer configurations

**Returns:**

* ``Dict[str, Any]``: Resolved serializer configuration

serialize_response
~~~~~~~~~~~~~~~~~~

.. autofunction:: apiout.serializer.serialize_response

Serializes API response using the provided serializer configuration.

**Parameters:**

* ``responses`` (Any): API response object(s)
* ``serializer_config`` (Dict[str, Any]): Serializer configuration

**Returns:**

* ``Any``: Serialized response

serialize_value
~~~~~~~~~~~~~~~

.. autofunction:: apiout.serializer.serialize_value

Converts a Python object to a JSON-serializable value.

**Parameters:**

* ``obj`` (Any): Object to serialize

**Returns:**

* ``Any``: JSON-serializable value

apply_field_mapping
~~~~~~~~~~~~~~~~~~~

.. autofunction:: apiout.serializer.apply_field_mapping

Applies field mapping configuration to an object.

**Parameters:**

* ``obj`` (Any): Object to process
* ``field_config`` (Dict[str, Any]): Field mapping configuration

**Returns:**

* ``Any``: Mapped result

call_method_or_attr
~~~~~~~~~~~~~~~~~~~

.. autofunction:: apiout.serializer.call_method_or_attr

Calls a method or accesses an attribute on an object.

**Parameters:**

* ``obj`` (Any): Object to access
* ``name`` (str): Method or attribute name

**Returns:**

* ``Any``: Result of method call or attribute value

introspect_and_generate
~~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: apiout.generator.introspect_and_generate

Introspects an API response and generates a TOML serializer configuration.

**Parameters:**

* ``module`` (str): Python module name
* ``client_class`` (str): Client class name
* ``method`` (str): Method name to call
* ``url`` (str): API URL
* ``params`` (Dict[str, Any]): API parameters
* ``name`` (str): Serializer name

**Returns:**

* ``str``: TOML serializer configuration

analyze_object
~~~~~~~~~~~~~~

.. autofunction:: apiout.generator.analyze_object

Analyzes an object's structure and returns metadata about its attributes and methods.

**Parameters:**

* ``obj`` (Any): Object to analyze
* ``depth`` (int): Maximum recursion depth
* ``visited`` (Optional[Set[int]]): Set of visited object IDs

**Returns:**

* ``Dict[str, Any]``: Object analysis metadata

generate_serializer_config
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: apiout.generator.generate_serializer_config

Generates a serializer configuration dictionary from object analysis.

**Parameters:**

* ``analysis`` (Dict[str, Any]): Object analysis metadata
* ``name`` (str): Serializer name

**Returns:**

* ``str``: TOML serializer configuration

Classes
-------

Configuration Structure
~~~~~~~~~~~~~~~~~~~~~~~

API Configuration
^^^^^^^^^^^^^^^^^

.. code-block:: python

   {
       "name": str,              # Required: API identifier
       "module": str,            # Required: Python module name
       "client_class": str,      # Optional: Client class name (default: "Client")
       "method": str,            # Required: Method name to call
       "url": str,               # Required: API URL
       "serializer": str | dict, # Optional: Serializer reference or config
       "params": dict            # Optional: API parameters
   }

Serializer Configuration
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   {
       "fields": {
           "output_field": str,  # Simple attribute mapping
           "nested_field": {
               "method": str,    # Method to call
               "fields": dict    # Nested field mappings
           },
           "collection": {
               "iterate": {
                   "count": str,      # Method returning count
                   "item": str,       # Method taking index
                   "fields": dict     # Fields for each item
               }
           }
       }
   }

Error Handling
--------------

Common Error Types
~~~~~~~~~~~~~~~~~~

Import Errors
^^^^^^^^^^^^^

.. code-block:: python

   {
       "error": "Failed to import module: ModuleNotFoundError: No module named 'xxx'"
   }

Attribute Errors
^^^^^^^^^^^^^^^^

.. code-block:: python

   {
       "error": "Failed to access class or method: 'module' object has no attribute 'Class'"
   }

API Call Errors
^^^^^^^^^^^^^^^

.. code-block:: python

   {
       "error": "Failed to fetch data: <exception details>"
   }

Usage Examples
--------------

Programmatic Usage
~~~~~~~~~~~~~~~~~~

Basic Fetch
^^^^^^^^^^^

.. code-block:: python

   from apiout.fetcher import fetch_api_data

   api_config = {
       "name": "weather",
       "module": "openmeteo_requests",
       "client_class": "Client",
       "method": "weather_api",
       "url": "https://api.open-meteo.com/v1/forecast",
       "params": {
           "latitude": 52.52,
           "longitude": 13.41,
           "current": ["temperature_2m"]
       }
   }

   result = fetch_api_data(api_config)
   print(result)

With Serializer
^^^^^^^^^^^^^^^

.. code-block:: python

   from apiout.fetcher import fetch_api_data

   api_config = {
       "name": "weather",
       "module": "openmeteo_requests",
       "method": "weather_api",
       "url": "https://api.open-meteo.com/v1/forecast",
       "serializer": "openmeteo",
       "params": {"latitude": 52.52, "longitude": 13.41}
   }

   global_serializers = {
       "openmeteo": {
           "fields": {
               "latitude": "Latitude",
               "longitude": "Longitude",
               "current": {
                   "method": "Current",
                   "fields": {"time": "Time"}
               }
           }
       }
   }

   result = fetch_api_data(api_config, global_serializers)
   print(result)

Custom Serialization
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from apiout.serializer import serialize_response, apply_field_mapping

   # Assuming you have a response object
   response = api_call()

   # Define field mapping
   field_config = {
       "id": "Id",
       "name": "Name",
       "data": {
           "method": "GetData",
           "fields": {
               "value": "Value",
               "timestamp": "Timestamp"
           }
       }
   }

   # Apply mapping
   result = apply_field_mapping(response, field_config)
   print(result)

Generate Configuration
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from apiout.generator import introspect_and_generate

   config = introspect_and_generate(
       module="openmeteo_requests",
       client_class="Client",
       method="weather_api",
       url="https://api.open-meteo.com/v1/forecast",
       params={"latitude": 52.52, "longitude": 13.41},
       name="openmeteo"
   )

   print(config)  # TOML serializer configuration
