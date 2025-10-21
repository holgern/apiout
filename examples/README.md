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

1. Define a reusable client configuration with `init_method` and `init_params`
2. Share the client instance across multiple API calls by referencing it
3. Call multiple methods on the same instance without re-fetching data
4. Use the simplified `ApiClient` class for easy programmatic access

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

### Using ApiClient in Your Code

The simplified `ApiClient` class makes it easy to use apiout programmatically:

```python
from apiout import ApiClient

# Load config and initialize
client = ApiClient("btcpriceticker.toml")

# Fetch data from all APIs
results = client.fetch()

# Access cached results (no re-fetch)
cached = client.get_results()

# Check success status
status = client.get_status()

# Get only successful results
successful = client.get_successful_results()
```

### How It Works

1. **Client Definition**: The `[clients.btc_price]` section defines the reusable client:

   - Creates `Price` instance with
     `init_params = {fiat = "EUR", days_ago = 1, service = "coinpaprika"}`
   - Calls `init_method = "update_service"` once to fetch price data

2. **First API** (`btc_price_usd`):

   - References `client = "btc_price"`
   - Calls `get_usd_price()` on the shared instance

3. **Subsequent APIs**:
   - All reference the same `client = "btc_price"`
   - No re-initialization or re-fetching
   - Simply call their respective methods on the cached data

### Configuration

The key features used:

```toml
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
```

**Benefits:**

- Single data fetch for multiple queries
- Consistent data across all method calls
- Improved performance by avoiding redundant operations

## Advanced Example: Mempool Post-Processor

- **Files**:
  - `mempool_apis.toml` - API and post-processor configuration with reusable client
  - `mempool_serializers.toml` - Serializer definitions
- **Python Example**: `multi_config_example.py`
- **Description**: Demonstrates combining multiple API calls with a post-processor using
  `pymempool`'s built-in `RecommendedFees` class

This example shows how to:

1. Define a reusable client configuration to eliminate repetition
2. Fetch data from multiple mempool endpoints using the same client
3. Combine and process the data using pymempool's `RecommendedFees` class
4. Serialize the processed output
5. Load multiple TOML configs in a single `ApiClient`

### Prerequisites

Install pymempool:

```bash
pip install pymempool
```

### Running the CLI Example

```bash
cd examples
apiout run -c mempool_apis.toml -s mempool_serializers.toml --json
```

Or from the project root:

```bash
apiout run -c examples/mempool_apis.toml -s examples/mempool_serializers.toml --json
```

### Running the Python Multi-Config Example

```bash
python examples/multi_config_example.py
```

This example demonstrates loading multiple config files with `ApiClient`:

```python
from apiout import ApiClient

# Load multiple configs at once
client = ApiClient([
    "btcpriceticker.toml",
    "mempool_apis.toml",
    "mempool_serializer.toml"
])

# Fetch from all APIs in all configs
results = client.fetch()

# Results contain data from all APIs:
# - btc_price_usd, btc_price_eur, etc. from btcpriceticker
# - block_tip_hash, recommended_fees, etc. from mempool
# - fee_analysis from post-processor
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

The example uses a reusable client configuration:

```toml
[clients.mempool]
module = "pymempool"
client_class = "MempoolAPI"
init_params = {api_base_url = "https://mempool.space/api/"}

[[apis]]
name = "block_tip_hash"
client = "mempool"
method = "get_block_tip_hash"

[[apis]]
name = "recommended_fees"
client = "mempool"
method = "get_recommended_fees"

[[post_processors]]
name = "fee_analysis"
module = "pymempool"
class = "RecommendedFees"
inputs = ["recommended_fees", "mempool_blocks_fee"]
serializer = "fee_analysis_serializer"
```

**Key Features:**

- **Reusable clients**: The `[clients.mempool]` section defines the client once
- **Client references**: Each API uses `client = "mempool"` instead of repeating
  configuration
- **No repetition**: All 5 APIs share the same client configuration
- **Post-processor**: Combines data from multiple APIs using pymempool's
  `RecommendedFees` class

This demonstrates how you can:

- Define a client configuration once and reference it multiple times
- Use **any existing Python class** from installed packages as a post-processor
- Eliminate configuration repetition for cleaner, more maintainable configs

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
