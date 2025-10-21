#!/usr/bin/env python3
"""
Example: Using ApiClient to fetch Bitcoin price data

This example demonstrates how to:
1. Use the simplified ApiClient class
2. Load a TOML configuration file automatically
3. Fetch data from multiple APIs with shared client instances
4. Access cached results without re-fetching
"""

import time
from pathlib import Path

from apiout import ApiClient


def main():
    config_path = Path(__file__).parent / "btcpriceticker.toml"

    client = ApiClient(config_path)

    print(f"Loaded {len(client.apis)} API endpoints")
    print(f"Using shared client: {client.apis[0].get('client', 'none')}\n")

    print("Fetching data (first run)...")
    start_time = time.time()
    results = client.fetch()
    end_time = time.time()
    print(f"First run completed in {end_time - start_time:.2f} seconds.\n")

    print("Fetching data again (reuses shared client)...")
    start_time = time.time()
    results = client.fetch()
    end_time = time.time()
    print(f"Second run completed in {end_time - start_time:.2f} seconds.\n")

    print("Accessing cached results (no fetch)...")
    cached_results = client.get_results()

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60 + "\n")

    for api_name, result in cached_results.items():
        status = "✓" if client.status[api_name]["success"] else "✗"
        print(f"{status} {api_name}: {result}")

    print("\n" + "=" * 60)
    print(f"Total APIs called: {len(results)}")
    print(f"Shared client instances: {len(client.shared_clients)}")
    print(f"Successful: {len(client.get_successful_results())}/{len(results)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
