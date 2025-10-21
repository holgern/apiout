# apiout Examples

This directory contains example configurations demonstrating how to use apiout.

## Basic Example: OpenMeteo Weather API

- **File**: `myapi.toml`
- **Description**: Fetches weather data from OpenMeteo API with inline serializers

Run it:

```bash
apiout run -c examples/myapi.toml --json
```

## Separate Configuration Example

- **Files**: `apis.toml` and `serializers.toml`
- **Description**: Demonstrates splitting API and serializer configurations

Run it:

```bash
apiout run -c examples/apis.toml -s examples/serializers.toml --json
```

## Shared Client Instance Example: Bitcoin Price Ticker

- **File**: `btcpriceticker.toml`
- **Python Example**: `btcpriceticker_example.py`
- **Description**: Demonstrates using shared client instances to fetch multiple data
  points from a single initialized client

This example shows how to:

1. Share a single client instance across multiple API calls using `client_id`
2. Initialize the client once with `init_method` and `init_params`
3. Call multiple methods on the same instance without re-fetching data

### Prerequisites

Install btcpriceticker:

```bash
pip install btcpriceticker
```

### Running the CLI Example

```bash
apiout run -c examples/btcpriceticker.toml --json
```

### Running the Python Example

```bash
python examples/btcpriceticker_example.py
```

Or from the project root:

```bash
python -m examples.btcpriceticker_example
```

### How It Works

1. **First API** (`btc_price_usd`):

   - Creates `Price` instance with
     `init_params = {fiat = "EUR", days_ago = 1, service = "coinpaprika"}`
   - Calls `update_service()` method once to fetch price data
   - Calls `get_usd_price()` and stores the instance with `client_id = "btc_price"`

2. **Subsequent APIs** (all others):
   - Reuse the same `Price` instance via `client_id = "btc_price"`
   - No re-initialization or re-fetching
   - Simply call their respective methods on the cached data

### Configuration

The key features used:

```toml
[[apis]]
name = "btc_price_usd"
client_id = "btc_price"           # Identifies shared instance
init_method = "update_service"    # Called once after instantiation
init_params = {fiat = "EUR", days_ago = 1, service = "coinpaprika"}
method = "get_usd_price"

[[apis]]
name = "btc_price_eur"
client_id = "btc_price"           # Reuses the same instance
method = "get_fiat_price"
```

**Benefits:**

- Single data fetch for multiple queries
- Consistent data across all method calls
- Improved performance by avoiding redundant operations

## Advanced Example: Mempool Post-Processor

- **Files**:
  - `mempool_apis.toml` - API and post-processor configuration
  - `mempool_serializers.toml` - Serializer definitions
- **Description**: Demonstrates combining multiple API calls with a post-processor using
  `pymempool`'s built-in `RecommendedFees` class

This example shows how to:

1. Fetch data from multiple mempool endpoints
2. Combine and process the data using pymempool's `RecommendedFees` class
3. Serialize the processed output

### Prerequisites

Install pymempool:

```bash
pip install pymempool
```

### Running the Example

```bash
cd examples
apiout run -c mempool_apis.toml -s mempool_serializers.toml --json
```

Or from the project root:

```bash
apiout run -c examples/mempool_apis.toml -s examples/mempool_serializers.toml --json
```

### How It Works

1. **APIs are fetched**: `recommended_fees` and `mempool_blocks_fee` are fetched from
   mempool.space
2. **Post-processor is executed**: pymempool's `RecommendedFees` class receives both API
   results as inputs
3. **Data is combined**: The class extracts fee data and calculates mempool statistics
4. **Output is serialized**: The result is formatted according to the
   `fee_analysis_serializer` configuration

### Configuration

The post-processor references pymempool's existing class:

```toml
[[post_processors]]
name = "fee_analysis"
module = "pymempool"
class = "RecommendedFees"
inputs = ["recommended_fees", "mempool_blocks_fee"]
serializer = "fee_analysis_serializer"
```

This demonstrates how you can use **any existing Python class** from installed packages
as a post-processor, without writing custom code.

## Creating Your Own Post-Processor

1. Create a Python class that accepts API results as constructor or method arguments
2. Process the data in your class
3. Configure it in your TOML file:

```toml
[[post_processors]]
name = "my_processor"
module = "my_module"
class = "MyProcessor"
inputs = ["api1", "api2"]
serializer = "my_serializer"  # Optional
```

The post-processor can:

- Combine data from multiple APIs
- Perform calculations and transformations
- Access earlier post-processor results (execute in order)
- Use serializers to format the output

## JSON Input Example

You can provide configuration as JSON via stdin instead of TOML files:

```bash
# Convert TOML to JSON with taplo
cd examples
taplo get -f mempool_apis.toml -o json | apiout run --json

# Or use inline JSON
echo '{
  "apis": [{
    "name": "test_api",
    "module": "requests",
    "method": "get",
    "url": "https://api.example.com"
  }]
}' | apiout run --json
```

This is useful for:

- Converting existing TOML configurations with tools like `taplo`
- Dynamically generating configurations in scripts
- Integration with JSON-based CI/CD workflows
