[![PyPI - Version](https://img.shields.io/pypi/v/apiout)](https://pypi.org/project/apiout/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/apiout)
![PyPI - Downloads](https://img.shields.io/pypi/dm/apiout)
[![codecov](https://codecov.io/gh/holgern/apiout/graph/badge.svg?token=AtcFpVooWk)](https://codecov.io/gh/holgern/apiout)

# apiout

A flexible Python tool for fetching data from APIs and serializing responses using TOML
configuration files.

## Features

- **Config-driven API calls**: Define API endpoints, parameters, and authentication in
  TOML files
- **Flexible serialization**: Map API responses to desired output formats using
  configurable field mappings
- **Separate concerns**: Keep API configurations and serializers in separate files for
  better organization
- **Default serialization**: Works without serializers - automatically converts objects
  to dictionaries
- **Generator tool**: Introspect API responses and auto-generate serializer
  configurations

## Installation

```bash
pip install -e .
```

## Quick Start

### 1. Basic Usage (No Serializers)

Create an API configuration file (`apis.toml`):

```toml
[[apis]]
name = "berlin_weather"
module = "openmeteo_requests"
client_class = "Client"
method = "weather_api"
url = "https://api.open-meteo.com/v1/forecast"

[apis.params]
latitude = 52.52
longitude = 13.41
current = ["temperature_2m"]
```

Run the API fetcher:

```bash
apiout run -c apis.toml --json
```

Without serializers, the tool will automatically convert the response objects to
dictionaries.

### 2. Using Serializers

Create a serializer configuration file (`serializers.toml`):

```toml
[serializers.openmeteo]
[serializers.openmeteo.fields]
latitude = "Latitude"
longitude = "Longitude"
timezone = "Timezone"

[serializers.openmeteo.fields.current]
method = "Current"
[serializers.openmeteo.fields.current.fields]
time = "Time"
temperature = "Temperature"
```

Update your API configuration to reference the serializer:

```toml
[[apis]]
name = "berlin_weather"
module = "openmeteo_requests"
client_class = "Client"
method = "weather_api"
url = "https://api.open-meteo.com/v1/forecast"
serializer = "openmeteo"  # Reference the serializer

[apis.params]
latitude = 52.52
longitude = 13.41
current = ["temperature_2m"]
```

Run with both configurations:

```bash
apiout run -c apis.toml -s serializers.toml --json
```

### 3. Inline Serializers

You can also define serializers inline in the API configuration:

```toml
[serializers.openmeteo]
[serializers.openmeteo.fields]
latitude = "Latitude"
longitude = "Longitude"

[[apis]]
name = "berlin_weather"
module = "openmeteo_requests"
method = "weather_api"
url = "https://api.open-meteo.com/v1/forecast"
serializer = "openmeteo"
```

Run with just the API config:

```bash
apiout run -c apis.toml --json
```

### 4. Environment Files

For cleaner configuration management, you can store reusable API configurations in
`~/.config/apiout/` and load them with the `-e`/`--env` flag:

**Setup:**

Create environment files in `~/.config/apiout/`:

```bash
# ~/.config/apiout/mempool.toml
[clients.mempool]
module = "requests"
client_class = "Session"

[serializers.mempool.block_data]
[serializers.mempool.block_data.fields]
hash = "id"
height = "height"
timestamp = "timestamp"

[[apis]]
name = "mempool_blocks"
client = "mempool"
method = "get"
url = "https://mempool.space/api/v1/blocks"
serializer = "block_data"
```

```bash
# ~/.config/apiout/btcprice.toml
[clients.btc_price]
module = "requests"
client_class = "Session"

[serializers.btc_price.price_data]
[serializers.btc_price.price_data.fields]
usd = "bitcoin.usd"
eur = "bitcoin.eur"

[[apis]]
name = "btc_price"
client = "btc_price"
method = "get"
url = "https://api.coingecko.com/api/v3/simple/price"
serializer = "price_data"
```

**Usage:**

```bash
# Load single environment
apiout run -e mempool --json

# Load multiple environments
apiout run -e mempool -e btcprice --json

# Mix environments with explicit configs
apiout run -e mempool -c custom.toml --json
```

**XDG Base Directory Support:**

The tool follows the XDG Base Directory specification:

- Uses `$XDG_CONFIG_HOME/apiout/` if set
- Falls back to `~/.config/apiout/` otherwise

See `examples/env_mempool.toml` and `examples/env_btcprice.toml` for complete examples.

### 5. User Parameters

Some APIs require runtime parameters that shouldn't be hardcoded in configuration files.
Use the `-p`/`--param` flag to provide these values:

**Configuration:**

```toml
[clients.mempool]
module = "pymempool"
client_class = "MempoolAPI"
init_params = {api_base_url = "https://mempool.space/api/"}

[[apis]]
name = "block_feerates"
client = "mempool"
method = "get_block_feerates"
user_inputs = ["time_period"]  # Declare required parameters
```

**Usage:**

```bash
# Single parameter
apiout run -c config.toml -p time_period=24h --json

# Multiple parameters
apiout run -c config.toml -p param1=value1 -p param2=value2 --json

# Combine with environments
apiout run -e mempool -p time_period=1w --json
```

**Features:**

- **Type coercion**: String values are automatically converted to `int` or `float` when
  possible (`"42"` → `42`, `"3.14"` → `3.14`)
- **Validation**: APIs with missing required parameters are skipped with a warning
- **Multiple parameters**: Support for APIs requiring multiple user inputs
- **Order matters**: Parameters are passed to methods in the order listed in
  `user_inputs`

## CLI Commands

### `run` - Fetch API Data

```bash
# Using environment files
apiout run -e <env_name> [--json]

# Using config files
apiout run -c <config.toml> [-s <serializers.toml>] [--json]

# Mix environments and config files
apiout run -e <env1> -e <env2> -c <config.toml> [--json]

# OR pipe JSON configuration from stdin
<json-source> | apiout run [--json]
```

**Options:**

- `-e, --env`: Environment name to load from `~/.config/apiout/` (can be specified
  multiple times)
- `-c, --config`: Path to API configuration file (TOML format, can be specified multiple
  times)
- `-s, --serializers`: Path to serializers configuration file (optional, can be
  specified multiple times)
- `-p, --param`: User parameter in format `key=value` (can be specified multiple times)
- `--json`: Output as JSON format (default: pretty-printed)

**Using JSON Input from stdin:**

When JSON is piped to stdin (and `-c` is not provided), apiout automatically detects and
parses it. This is useful for:

- Converting TOML to JSON with tools like `taplo`
- Dynamically generating configurations
- Integration with other tools and scripts

Example with `taplo`:

```bash
taplo get -f examples/mempool_apis.toml -o json | apiout run --json
```

Example with inline JSON:

```bash
echo '{"apis": [{"name": "block_height", "module": "pymempool", "client_class": "MempoolAPI", "method": "get_block_tip_height", "url": "https://mempool.space/api/"}]}' | apiout run --json
```

The JSON format matches the TOML structure:

```json
{
  "apis": [
    {
      "name": "api_name",
      "module": "module_name",
      "client_class": "Client",
      "method": "method_name",
      "url": "https://api.url",
      "params": {}
    }
  ],
  "post_processors": [...],
  "serializers": {...}
}
```

### `gen-api` - Generate API Config

Generate an API configuration TOML snippet:

```bash
apiout gen-api \
  --module pymempool \
  --client-class MempoolAPI \
  --client mempool \
  --method get_block_tip_hash \
  --name block_tip_hash \
  --init-params '{"api_base_url": "https://mempool.space/api/"}'
```

**Options:**

- `-m, --module`: Python module name (required)
- `--client-class`: Client class name (default: "Client")
- `--method`: Method name to call (required)
- `-n, --name`: API name (required)
- `--client`: Client reference name (optional: generates `[clients.X]` section)
- `--init-params`: JSON init params dict for client (optional)
- `-u, --url`: API URL (optional)
- `-p, --params`: JSON params dict (optional)
- `--user-inputs`: JSON array of required user input parameter names (optional)
- `--user-defaults`: JSON dict of default values for user inputs (optional)

### `gen-serializer` - Generate Serializer Config

Introspect an API response and generate a serializer configuration from an existing API
config:

```bash
# Generate serializer from API config
apiout gen-serializer --config examples/mempool_apis.toml --api block_tip_hash

# Using environment
apiout gen-serializer --env production --api recommended_fees
```

**Options:**

- `-a, --api`: API name from config (required)
- `-c, --config`: Config file(s) to load (can be specified multiple times)
- `-e, --env`: Environment name to load

**How it works:**

1. Loads the config file(s) and finds the API definition by name
2. Extracts all configuration details (module, client, method, url, params, init_params)
3. Makes an actual API call using the configured client
4. Introspects the response structure
5. Generates a serializer TOML configuration

**Example:**

Given a config file `mempool.toml`:

```toml
[clients.mempool]
module = "pymempool"
client_class = "MempoolAPI"
init_params = {api_base_url = "https://mempool.space/api/"}

[[apis]]
name = "block_tip_hash"
client = "mempool"
method = "get_block_tip_hash"
```

Running:

```bash
apiout gen-serializer --config mempool.toml --api block_tip_hash
```

Outputs:

```toml
[serializers.block_tip_hash_serializer]
[serializers.block_tip_hash_serializer.fields]
hash = "hash_value"
```

## Configuration Format

### API Configuration

```toml
[[apis]]
name = "api_name"              # Unique identifier for this API
module = "module_name"         # Python module to import
client_class = "Client"        # Class name (default: "Client")
method = "method_name"         # Method to call on the client
url = "https://api.url"        # API endpoint URL
serializer = "serializer_ref"  # Reference to serializer (optional)

[apis.params]                  # Parameters to pass to the method
key = "value"
```

### Serializer Configuration

```toml
[serializers.name]
[serializers.name.fields]
output_field = "InputAttribute"  # Map output field to object attribute

[serializers.name.fields.nested]
method = "MethodName"            # Call a method on the object
[serializers.name.fields.nested.fields]
nested_field = "NestedAttribute"

[serializers.name.fields.collection]
iterate = {
  count = "CountMethod",
  item = "ItemMethod",
  fields = { value = "Value" }
}
```

## Advanced Serializer Features

### Client-Scoped Serializers

When working with multiple clients, you can scope serializers to specific clients to
avoid namespace collisions:

```toml
# Define clients
[clients.btc_price]
module = "requests"
client_class = "Session"

[clients.mempool]
module = "pymempool"
client_class = "MempoolAPI"

# Global serializers (backward compatible)
[serializers.generic_data]
[serializers.generic_data.fields]
value = "data"

# Client-scoped serializers - nested under client names
[serializers.btc_price.price_data]
[serializers.btc_price.price_data.fields]
usd = "usd_price"
eur = "eur_price"

[serializers.mempool.price_data]
[serializers.mempool.price_data.fields]
sats_per_dollar = "price"
timestamp = "time"

# APIs automatically resolve serializers in client scope
[[apis]]
name = "btc_price"
client = "btc_price"
method = "get"
url = "https://api.example.com"
serializer = "price_data"  # Resolves to btc_price.price_data

[[apis]]
name = "mempool_price"
client = "mempool"
method = "get_price"
url = "https://mempool.space/api/"
serializer = "price_data"  # Resolves to mempool.price_data
```

**Resolution Order:**

1. Inline dict (highest priority)
2. Explicit dotted reference (e.g., `"client_name.serializer"`)
3. Client-scoped lookup (e.g., when API has `client = "foo"` and `serializer = "bar"`)
4. Global lookup (backward compatible)

See `examples/scoped_serializers_example.toml` for a complete example.

### Method Calls

Call methods on objects:

```toml
[serializers.example.fields.data]
method = "GetData"
[serializers.example.fields.data.fields]
value = "Value"
```

### Iteration

Iterate over collections:

```toml
[serializers.example.fields.items]
method = "GetContainer"
[serializers.example.fields.items.fields.variables]
iterate = {
  count = "Length",        # Method that returns count
  item = "GetItem",        # Method that takes index and returns item
  fields = {
    name = "Name",         # Fields to extract from each item
    value = "Value"
  }
}
```

### NumPy Array Support

The serializer automatically converts NumPy arrays to lists:

```toml
[serializers.example.fields.data]
values = "ValuesAsNumpy"  # Returns numpy array, auto-converted to list
```

## Post-Processors

Post-processors allow you to combine and transform data from multiple API calls into a
single result. This is useful when you need to:

- Aggregate data from multiple endpoints
- Perform calculations using multiple API responses
- Create custom data structures from API results

### Configuration Format

```toml
[[post_processors]]
name = "processor_name"          # Unique identifier
module = "module_name"           # Python module containing the processor
class = "ProcessorClass"         # Class to instantiate
method = "process"               # Optional: method to call (default: use __init__)
inputs = ["api1", "api2"]        # List of API result names to pass as inputs
serializer = "serializer_ref"    # Optional: serializer for the output
```

### How It Works

1. All APIs defined in `[[apis]]` sections are fetched first
2. Post-processors are executed in order, receiving API results as inputs
3. Each post-processor's result is added to the results dictionary
4. Later post-processors can use outputs from earlier post-processors

### Example: Combining Mempool Data

This example uses the `pymempool` library's built-in `RecommendedFees` class as a
post-processor:

```toml
# Define the APIs
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

# Define the post-processor using pymempool's RecommendedFees class
[[post_processors]]
name = "fee_analysis"
module = "pymempool"
class = "RecommendedFees"
inputs = ["recommended_fees", "mempool_blocks_fee"]
serializer = "fee_analysis_serializer"
```

Define the serializer for the post-processor output:

```toml
[serializers.fee_analysis_serializer]
[serializers.fee_analysis_serializer.fields]
fastest_fee = "fastest_fee"
half_hour_fee = "half_hour_fee"
hour_fee = "hour_fee"
mempool_tx_count = "mempool_tx_count"
mempool_vsize = "mempool_vsize"
mempool_blocks = "mempool_blocks"
```

Run it:

```bash
apiout run -c mempool_apis.toml -s mempool_serializers.toml --json
```

The output will include the `fee_analysis` result with all combined data from both APIs.

## Examples

See the included `myapi.toml` for a complete example with the OpenMeteo API, or check
the separate `apis.toml` and `serializers.toml` files for the split configuration
approach.

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Coverage

```bash
pytest tests/ --cov=apiout --cov-report=html
```

## License

MIT
