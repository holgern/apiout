# apiout

A flexible Python tool for fetching data from APIs and serializing responses using TOML configuration files.

## Features

- **Config-driven API calls**: Define API endpoints, parameters, and authentication in TOML files
- **Flexible serialization**: Map API responses to desired output formats using configurable field mappings
- **Separate concerns**: Keep API configurations and serializers in separate files for better organization
- **Default serialization**: Works without serializers - automatically converts objects to dictionaries
- **Generator tool**: Introspect API responses and auto-generate serializer configurations

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

Without serializers, the tool will automatically convert the response objects to dictionaries.

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

## CLI Commands

### `run` - Fetch API Data

```bash
apiout run -c <config.toml> [-s <serializers.toml>] [--json]
```

**Options:**
- `-c, --config`: Path to API configuration file (required)
- `-s, --serializers`: Path to serializers configuration file (optional)
- `--json`: Output as JSON format (default: pretty-printed)

### `generate` - Generate Serializer Config

Introspect an API response and generate a serializer configuration:

```bash
apiout generate \
  --module openmeteo_requests \
  --client-class Client \
  --method weather_api \
  --url "https://api.open-meteo.com/v1/forecast" \
  --params '{"latitude": 52.52, "longitude": 13.41, "current": ["temperature_2m"]}' \
  --name openmeteo
```

**Options:**
- `-m, --module`: Python module name (required)
- `-c, --client-class`: Client class name (default: "Client")
- `--method`: Method name to call (required)
- `-u, --url`: API URL (required)
- `-p, --params`: JSON params dict (default: "{}")
- `-n, --name`: Serializer name (default: "generated")

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

## Examples

See the included `myapi.toml` for a complete example with the OpenMeteo API, or check the separate `apis.toml` and `serializers.toml` files for the split configuration approach.

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
