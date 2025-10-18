Examples
========

This page provides practical examples of using **apiout** for various use cases.

Weather API Example
-------------------

OpenMeteo API Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetch weather data from the OpenMeteo API with full serialization.

**Configuration Files**

``apis.toml``:

.. code-block:: toml

   [[apis]]
   name = "berlin_weather"
   module = "openmeteo_requests"
   client_class = "Client"
   method = "weather_api"
   url = "https://api.open-meteo.com/v1/forecast"
   serializer = "openmeteo"

   [apis.params]
   latitude = 52.52
   longitude = 13.41
   hourly = ["temperature_2m", "precipitation", "wind_speed_10m"]
   current = ["temperature_2m", "relative_humidity_2m"]

``serializers.toml``:

.. code-block:: toml

   [serializers.openmeteo]
   [serializers.openmeteo.fields]
   latitude = "Latitude"
   longitude = "Longitude"
   elevation = "Elevation"
   timezone = "Timezone"
   timezone_abbreviation = "TimezoneAbbreviation"
   utc_offset_seconds = "UtcOffsetSeconds"

   [serializers.openmeteo.fields.current]
   method = "Current"
   [serializers.openmeteo.fields.current.fields]
   time = "Time"
   [serializers.openmeteo.fields.current.fields.variables]
   iterate = {
     count = "VariablesLength",
     item = "Variables",
     fields = { value = "Value" }
   }

   [serializers.openmeteo.fields.hourly]
   method = "Hourly"
   [serializers.openmeteo.fields.hourly.fields]
   time = "Time"
   time_end = "TimeEnd"
   interval = "Interval"
   [serializers.openmeteo.fields.hourly.fields.variables]
   iterate = {
     count = "VariablesLength",
     item = "Variables",
     fields = { values = "ValuesAsNumpy" }
   }

**Running the Example**

.. code-block:: bash

   apiout run -c examples/apis.toml -s examples/serializers.toml --json

**Expected Output**

.. code-block:: json

   {
     "berlin_weather": [
       {
         "latitude": 52.52,
         "longitude": 13.41,
         "elevation": 38.0,
         "timezone": "GMT",
         "timezone_abbreviation": "GMT",
         "utc_offset_seconds": 0,
         "current": {
           "time": 1760711400,
           "variables": [
             {"value": 12.15},
             {"value": 59.0}
           ]
         },
         "hourly": {
           "time": 1760659200,
           "time_end": 1761264000,
           "interval": 3600,
           "variables": [
             {"values": [11.5, 11.1, 11.0, ...]},
             {"values": [0.0, 0.0, 0.0, ...]},
             {"values": [12.3, 11.8, 10.5, ...]}
           ]
         }
       }
     ]
   }

Multiple Cities
~~~~~~~~~~~~~~~

Fetch weather for multiple cities in one configuration:

.. code-block:: toml

   [[apis]]
   name = "berlin_weather"
   module = "openmeteo_requests"
   client_class = "Client"
   method = "weather_api"
   url = "https://api.open-meteo.com/v1/forecast"
   serializer = "openmeteo"

   [apis.params]
   latitude = 52.52
   longitude = 13.41
   current = ["temperature_2m"]

   [[apis]]
   name = "munich_weather"
   module = "openmeteo_requests"
   client_class = "Client"
   method = "weather_api"
   url = "https://api.open-meteo.com/v1/forecast"
   serializer = "openmeteo"

   [apis.params]
   latitude = 48.1351
   longitude = 11.5820
   current = ["temperature_2m"]

Default Serialization Example
------------------------------

Testing Without Serializers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When exploring a new API, start without serializers to see the raw structure:

.. code-block:: toml

   [[apis]]
   name = "test_api"
   module = "requests"
   client_class = "Session"
   method = "get"
   url = "https://api.example.com/data"

Run without serializer config:

.. code-block:: bash

   apiout run -c config.toml --json

apiout will automatically convert objects to dictionaries, showing all public attributes.

Generator Example
-----------------

Auto-Generate Serializer Config
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use the generator to create an initial serializer configuration:

.. code-block:: bash

   apiout generate \
     --module openmeteo_requests \
     --client-class Client \
     --method weather_api \
     --url "https://api.open-meteo.com/v1/forecast" \
     --params '{"latitude": 52.52, "longitude": 13.41, "current": ["temperature_2m"]}' \
     --name openmeteo > serializers.toml

This introspects the API response and generates a TOML config you can refine.

Nested Objects Example
----------------------

Complex Data Structures
~~~~~~~~~~~~~~~~~~~~~~~

Handle deeply nested API responses:

.. code-block:: toml

   [serializers.complex]
   [serializers.complex.fields]
   id = "Id"
   name = "Name"

   [serializers.complex.fields.metadata]
   method = "GetMetadata"
   [serializers.complex.fields.metadata.fields]
   created = "CreatedAt"
   updated = "UpdatedAt"

   [serializers.complex.fields.metadata.fields.author]
   method = "GetAuthor"
   [serializers.complex.fields.metadata.fields.author.fields]
   name = "Name"
   email = "Email"

This creates a structure like:

.. code-block:: json

   {
     "id": 123,
     "name": "Example",
     "metadata": {
       "created": "2025-01-01",
       "updated": "2025-01-15",
       "author": {
         "name": "John Doe",
         "email": "john@example.com"
       }
     }
   }

Collection Iteration Example
-----------------------------

Processing Lists of Items
~~~~~~~~~~~~~~~~~~~~~~~~~

Iterate over collections of objects:

.. code-block:: toml

   [serializers.collection]
   [serializers.collection.fields]
   total = "TotalCount"

   [serializers.collection.fields.items]
   iterate = {
     count = "ItemCount",
     item = "GetItem",
     fields = {
       id = "Id",
       name = "Name",
       price = "Price"
     }
   }

Result:

.. code-block:: json

   {
     "total": 10,
     "items": [
       {"id": 1, "name": "Item 1", "price": 9.99},
       {"id": 2, "name": "Item 2", "price": 19.99},
       ...
     ]
   }

Inline Serializer Example
--------------------------

Single-File Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

For small projects, keep everything in one file:

.. code-block:: toml

   [serializers.simple]
   [serializers.simple.fields]
   value = "Value"
   timestamp = "Timestamp"

   [[apis]]
   name = "simple_api"
   module = "my_module"
   client_class = "Client"
   method = "fetch_data"
   url = "https://api.example.com"
   serializer = "simple"

   [apis.params]
   key = "value"

Run with just the config file:

.. code-block:: bash

   apiout run -c config.toml --json

Python Integration Example
---------------------------

Using apiout Programmatically
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from apiout.fetcher import fetch_api_data

   api_config = {
       "name": "test_api",
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

With Custom Serializer
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from apiout.fetcher import fetch_api_data

   api_config = {
       "name": "test_api",
       "module": "openmeteo_requests",
       "method": "weather_api",
       "url": "https://api.open-meteo.com/v1/forecast",
       "serializer": "openmeteo",
       "params": {"latitude": 52.52, "longitude": 13.41}
   }

   serializers = {
       "openmeteo": {
           "fields": {
               "latitude": "Latitude",
               "longitude": "Longitude"
           }
       }
   }

   result = fetch_api_data(api_config, serializers)
   print(result)

Pipeline Integration Example
-----------------------------

Using in Data Pipelines
~~~~~~~~~~~~~~~~~~~~~~~

Integrate apiout into data processing pipelines:

.. code-block:: bash

   # Fetch data and pipe to jq for filtering
   apiout run -c config.toml --json | jq '.berlin_weather[0].current'

   # Save to file
   apiout run -c config.toml --json > weather_data.json

   # Pipe to Python for processing
   apiout run -c config.toml --json | python process_weather.py

Combining Multiple APIs
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Run multiple configs and merge results
   {
     echo "{"
     apiout run -c weather.toml --json | jq -r '.berlin_weather'
     echo ","
     apiout run -c stocks.toml --json | jq -r '.stock_data'
     echo "}"
   } | jq -s '.[0]'

Post-Processor Example
----------------------

Combining Multiple API Results
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Post-processors allow you to combine and transform data from multiple API calls using any Python class.

**Configuration**

``mempool_apis.toml``:

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

**Running the Example**

.. code-block:: bash

   pip install pymempool
   apiout run -c mempool_apis.toml -s mempool_serializers.toml --json

**How It Works**

1. Both APIs are fetched first: ``recommended_fees`` and ``mempool_blocks_fee``
2. The post-processor instantiates ``pymempool.RecommendedFees`` with both results
3. The output is serialized using ``fee_analysis_serializer``
4. The result appears in the output under the name ``fee_analysis``

**Configuration Format**

.. code-block:: toml

   [[post_processors]]
   name = "processor_name"          # Required: unique identifier
   module = "module_name"           # Required: Python module
   class = "ClassName"              # Required: class to instantiate
   method = "method_name"           # Optional: method to call
   inputs = ["api1", "api2"]        # Required: list of API names
   serializer = "serializer_name"   # Optional: serializer reference

**Key Features**

* Use any existing Python class from installed packages
* Combine data from multiple API calls
* Chain multiple post-processors together
* Optional serialization of output
* Later post-processors can reference earlier ones

**Example Use Cases**

* Combining fee data from multiple endpoints (as shown above)
* Calculating statistics across multiple API responses
* Aggregating data from different sources
* Transforming API responses into domain objects
