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
* ``init_params``: Parameters to pass to the client class constructor
* ``client``: Reference to a client configuration from the ``[clients]`` section

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

Reusable Client Configurations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When multiple APIs use the same client with identical initialization parameters, you can define the client once in a ``[clients]`` section and reference it from multiple APIs. This eliminates repetition and makes configurations easier to maintain.

**Client references automatically create shared instances** - all APIs referencing the same client will share one instance.

Configuration
^^^^^^^^^^^^^

.. code-block:: toml

   [clients.mempool]
   module = "pymempool"
   client_class = "MempoolAPI"
   init_params = {api_base_url = "https://mempool.space/api/"}

   [[apis]]
   name = "block_tip_hash"
   client = "mempool"
   method = "get_block_tip_hash"

   [[apis]]
   name = "block_tip_height"
   client = "mempool"
   method = "get_block_tip_height"

   [[apis]]
   name = "recommended_fees"
   client = "mempool"
   method = "get_recommended_fees"

With Init Method
^^^^^^^^^^^^^^^^

For clients that require initialization before use, specify ``init_method`` in the client definition:

.. code-block:: toml

   [clients.btc_price]
   module = "btcpriceticker"
   client_class = "Price"
   init_params = {fiat = "EUR", days_ago = 1, service = "coinpaprika"}
   init_method = "update_service"

   [[apis]]
   name = "btc_price_usd"
   client = "btc_price"
   method = "get_usd_price"

   [[apis]]
   name = "btc_price_eur"
   client = "btc_price"
   method = "get_fiat_price"

The ``init_method`` is called **once** when the client is first created. All subsequent APIs reuse the same instance without re-initialization.

How It Works
^^^^^^^^^^^^

1. Define a client in the ``[clients.<name>]`` section with:

   * ``module``: Python module containing the client class
   * ``client_class``: Name of the client class
   * ``init_params``: Parameters to pass to the constructor (optional)
   * ``init_method``: Method to call once after instantiation (optional)

2. Reference the client from APIs using ``client = "<name>"``

3. The client is instantiated **once** when first referenced

4. If ``init_method`` is specified, it's called after instantiation

5. All APIs referencing the same client share this instance

6. Only the ``method`` and ``params`` need to be specified for each API

Benefits
^^^^^^^^

* **Eliminate Repetition**: Define client configuration once, reference it multiple times
* **Easier Maintenance**: Update client settings in one place
* **Cleaner Configs**: Focus on what each API does, not how to initialize the client
* **Automatic Sharing**: All APIs using the same client reference share one instance
* **Performance**: Avoid redundant initialization and data fetching

Compatibility
^^^^^^^^^^^^^

The ``client`` reference can be used alongside traditional configuration:

* If ``client`` is specified, ``module``, ``client_class``, and ``init_params`` are taken from the client definition
* Inline ``init_params`` can override or extend client-level ``init_params``
* If no ``client`` is specified, traditional inline configuration is used

Multiple Configuration Files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Client definitions are merged from multiple configuration files:

.. code-block:: bash

   apiout run -c base.toml -c apis.toml

If the same client name appears in multiple files, later files override earlier ones.

Multiple Configuration Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use multiple configuration and serializer files with the ``-c`` and ``-s`` options:

.. code-block:: bash

   apiout run -c base.toml -c apis.toml -c more_apis.toml -s serializers1.toml -s serializers2.toml

Merging Behavior
^^^^^^^^^^^^^^^^

* **APIs**: Appended in order (base → apis → more_apis)
* **Post-processors**: Appended in order
* **Serializers**: Merged (later files override earlier ones)

This allows you to:

* Share common configurations across projects
* Override serializers for different environments
* Organize large configurations into multiple files

Post-Processors
~~~~~~~~~~~~~~~

Post-processors allow you to combine and transform data from multiple API calls using any Python class.

Configuration Format
^^^^^^^^^^^^^^^^^^^^

.. code-block:: toml

   [[post_processors]]
   name = "processor_name"          # Required: unique identifier
   module = "module_name"           # Required: Python module
   class = "ClassName"              # Required: class to instantiate
   method = "method_name"           # Optional: method to call
   inputs = ["api1", "api2"]        # Required: list of API names
   serializer = "serializer_name"   # Optional: serializer reference

Execution Order
^^^^^^^^^^^^^^^

1. All ``[[apis]]`` are fetched first and stored in a results dictionary
2. Post-processors execute in the order they appear in the configuration
3. Each post-processor receives the specified API results as arguments
4. The class is instantiated with the inputs (or a method is called if specified)
5. The result is optionally serialized
6. The result is added to the output under the post-processor's name
7. Later post-processors can reference outputs from earlier ones

Example
^^^^^^^

.. code-block:: toml

   [[apis]]
   name = "recommended_fees"
   module = "pymempool"
   client_class = "MempoolAPI"
   method = "get_recommended_fees"
   url = "https://mempool.space/api/"

   [[apis]]
   name = "mempool_blocks_fee"
   module = "pymempool"
   client_class = "MempoolAPI"
   method = "get_mempool_blocks_fee"
   url = "https://mempool.space/api/"

   [[post_processors]]
   name = "fee_analysis"
   module = "pymempool"
   class = "RecommendedFees"
   inputs = ["recommended_fees", "mempool_blocks_fee"]
   serializer = "fee_analysis_serializer"

Benefits
^^^^^^^^

* **Declarative Configuration**: Define data transformation in TOML instead of code
* **Reusability**: Post-processors can be reused across different configurations
* **Modularity**: Separate data fetching from data processing
* **Composability**: Chain multiple post-processors together
* **Integration**: Use any existing Python class from installed packages

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

JSON Input
~~~~~~~~~~

Instead of using TOML configuration files, you can provide JSON configuration via stdin:

.. code-block:: bash

   apiout run --json < config.json

This is useful for:

* Converting TOML to JSON with tools like ``taplo``
* Dynamically generating configurations
* Integration with JSON-based workflows

**Example: Convert TOML to JSON**

.. code-block:: bash

   taplo get -f apis.toml -o json | apiout run --json

**Example: Inline JSON**

.. code-block:: bash

   echo '{"apis": [{"name": "test", "module": "requests", "method": "get", "url": "https://api.example.com"}]}' | apiout run --json

The JSON structure matches the TOML format exactly:

.. code-block:: json

   {
     "apis": [
       {
         "name": "api_name",
         "module": "module_name",
         "client_class": "Client",
         "method": "method_name",
         "url": "https://api.url",
         "serializer": "serializer_ref",
         "params": {
           "key": "value"
         }
       }
     ],
     "serializers": {
       "serializer_name": {
         "fields": {
           "output_field": "InputAttribute"
         }
       }
     }
   }

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
