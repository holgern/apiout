User Guide
==========

This guide provides detailed information on configuring and using **apiout**.

Configuration Files
-------------------

API Configuration
~~~~~~~~~~~~~~~~~

The API configuration file defines which APIs to call and their parameters.

Basic Structure
^^^^^^^^^^^^^^^

.. code-block:: toml

   [[apis]]
   name = "api_name"              # Unique identifier for this API
   module = "module_name"         # Python module to import
   client_class = "Client"        # Class name (default: "Client")
   method = "method_name"         # Method to call on the client
   url = "https://api.url"        # API endpoint URL
   serializer = "serializer_ref"  # Reference to serializer (optional)

   [apis.params]                  # Parameters to pass to the method
   key = "value"

Required Fields
^^^^^^^^^^^^^^^

* ``name``: Unique identifier for the API
* ``module``: Python module containing the client class
* ``method``: Method name to call on the client instance
* ``url``: API endpoint URL

Optional Fields
^^^^^^^^^^^^^^^

* ``client_class``: Name of the client class (default: "Client")
* ``serializer``: Reference to a serializer configuration (string) or inline serializer (dict)
* ``params``: Dictionary of parameters to pass to the API method

Multiple APIs
^^^^^^^^^^^^^

You can define multiple APIs in one file:

.. code-block:: toml

   [[apis]]
   name = "api1"
   module = "module1"
   method = "method1"
   url = "https://api1.example.com"

   [apis.params]
   key = "value"

   [[apis]]
   name = "api2"
   module = "module2"
   method = "method2"
   url = "https://api2.example.com"

   [apis.params]
   key = "value"

Serializer Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

Serializers define how to transform API response objects into structured data.

Basic Structure
^^^^^^^^^^^^^^^

.. code-block:: toml

   [serializers.name]
   [serializers.name.fields]
   output_field = "InputAttribute"

Field Mapping Types
^^^^^^^^^^^^^^^^^^^

**Simple Attribute Access**

.. code-block:: toml

   [serializers.example.fields]
   latitude = "Latitude"      # result["latitude"] = obj.Latitude
   longitude = "Longitude"    # result["longitude"] = obj.Longitude

**Method Calls**

.. code-block:: toml

   [serializers.example.fields.current]
   method = "Current"         # Call obj.Current() method
   [serializers.example.fields.current.fields]
   time = "Time"             # result["current"]["time"] = obj.Current().Time

**Nested Objects**

.. code-block:: toml

   [serializers.example.fields.data]
   method = "GetData"
   [serializers.example.fields.data.fields]
   value = "Value"
   status = "Status"

**Iteration**

Iterate over collections with indexed access:

.. code-block:: toml

   [serializers.example.fields.variables]
   iterate = {
     count = "VariablesLength",    # Method returning item count
     item = "Variables",            # Method taking index parameter
     fields = { value = "Value" }  # Fields to extract from each item
   }

**Iteration with Method**

.. code-block:: toml

   [serializers.example.fields.data]
   method = "GetContainer"
   [serializers.example.fields.data.fields.variables]
   iterate = {
     count = "Length",
     item = "GetItem",
     fields = { name = "Name", value = "Value" }
   }

Serializer Referencing
~~~~~~~~~~~~~~~~~~~~~~

Inline Serializers
^^^^^^^^^^^^^^^^^^

Define serializers in the same file as APIs:

.. code-block:: toml

   [serializers.myserializer]
   [serializers.myserializer.fields]
   field1 = "Attribute1"

   [[apis]]
   name = "myapi"
   serializer = "myserializer"
   # ... rest of config

Separate Serializers File
^^^^^^^^^^^^^^^^^^^^^^^^^^

Keep serializers in a separate file for better organization:

``serializers.toml``:

.. code-block:: toml

   [serializers.myserializer]
   [serializers.myserializer.fields]
   field1 = "Attribute1"

``apis.toml``:

.. code-block:: toml

   [[apis]]
   name = "myapi"
   serializer = "myserializer"
   # ... rest of config

Run with both files:

.. code-block:: bash

   apiout run -c apis.toml -s serializers.toml

Priority Order
^^^^^^^^^^^^^^

When using both inline and separate serializer files:

1. Serializers from ``-s`` file are loaded first
2. Inline serializers from config file are merged in
3. Inline serializers override external ones with the same name

No Serializer
^^^^^^^^^^^^^

If no serializer is specified, apiout uses default serialization:

* Primitive types (str, int, float, bool, None) are returned as-is
* Lists and tuples are recursively serialized
* Dictionaries are recursively serialized
* Objects are converted to dictionaries (public attributes only)
* NumPy arrays are converted to lists

Advanced Features
-----------------

NumPy Array Handling
~~~~~~~~~~~~~~~~~~~~

NumPy arrays are automatically converted to Python lists:

.. code-block:: toml

   [serializers.example.fields.data]
   values = "ValuesAsNumpy"  # Returns numpy array, auto-converted to list

Generator Tool
~~~~~~~~~~~~~~

The generator tool introspects API responses and generates serializer configurations:

.. code-block:: bash

   apiout generate \
     --module openmeteo_requests \
     --method weather_api \
     --url "https://api.open-meteo.com/v1/forecast" \
     --params '{"latitude": 52.52, "longitude": 13.41, "current": ["temperature_2m"]}' \
     --name openmeteo > serializers.toml

This outputs a TOML serializer configuration that you can refine manually.

Output Formats
~~~~~~~~~~~~~~

**JSON Output**

.. code-block:: bash

   apiout run -c config.toml --json

Outputs valid JSON for piping to other tools:

.. code-block:: json

   {
     "api_name": [
       {
         "field1": "value1",
         "field2": "value2"
       }
     ]
   }

**Pretty Print (Default)**

.. code-block:: bash

   apiout run -c config.toml

Uses Rich console formatting for readable output.

Error Handling
--------------

apiout provides clear error messages for common issues:

* Missing configuration file
* Invalid TOML syntax
* Missing required fields
* Module import errors
* API call failures

All errors are displayed with context to help diagnose issues quickly.

Best Practices
--------------

1. **Separate Concerns**: Keep API configs and serializers in separate files for large projects
2. **Use Descriptive Names**: Give APIs and serializers clear, descriptive names
3. **Start Without Serializers**: Test API calls with default serialization first
4. **Use Generator**: Generate initial serializer configs, then refine manually
5. **Version Control**: Store config files in version control
6. **Document Custom Serializers**: Add comments to explain complex field mappings
