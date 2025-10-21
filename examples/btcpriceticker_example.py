#!/usr/bin/env python3
"""
Example: Using apiout programmatically to fetch Bitcoin price data

This example demonstrates how to:
1. Load a TOML configuration file
2. Use apiout's fetcher to call multiple APIs with shared client instances
3. Process and display the results
"""

import tomli
import time
from pathlib import Path
from apiout.fetcher import fetch_api_data


def main():
    config_path = Path(__file__).parent / "btcpriceticker.toml"

    with open(config_path, "rb") as f:
        config = tomli.load(f)

    apis = config.get("apis", [])

    if not apis:
        print("No APIs found in configuration")
        return

    print(f"Fetching data from {len(apis)} API endpoints...")
    print(f"Using shared client with ID: {apis[0].get('client_id', 'none')}\n")

    shared_clients = {}
    results = {}
    start_time = time.time()
    for api_config in apis:
        api_name = api_config.get("name", "unknown")
        print(f"Calling {api_name}...", end=" ")

        result = fetch_api_data(api_config, shared_clients=shared_clients)
        results[api_name] = result

        print(f"✓")
    end_time = time.time()
    print(f"\nFirst run completed in {end_time - start_time:.2f} seconds.\n")
    print("Retry with the shared_client")
    start_time = time.time()
    for api_config in apis:
        api_name = api_config.get("name", "unknown")
        print(f"Calling {api_name}...", end=" ")

        result = fetch_api_data(api_config, shared_clients=shared_clients)
        results[api_name] = result

        print(f"✓")
    end_time = time.time()
    print(f"\nSecond run completed in {end_time - start_time:.2f} seconds.\n")
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60 + "\n")

    for api_name, result in results.items():
        print(f"{api_name}:")
        print(f"  {result}")

    print("\n" + "=" * 60)
    print(f"Total APIs called: {len(results)}")
    print(f"Shared client instances created: {len(shared_clients)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
