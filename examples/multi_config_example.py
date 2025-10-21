#!/usr/bin/env python3
"""
Example: Using ApiClient to load multiple TOML configs and fetch data

This example demonstrates:
1. Loading multiple TOML configs (btcpriceticker, mempool APIs, and serializers)
2. Fetching all APIs in one call
3. Accessing cached results without re-fetching
4. Checking success status for each API
"""

from pathlib import Path

from apiout import ApiClient


def main():
    config_dir = Path(__file__).parent

    client = ApiClient(
        [
            config_dir / "btcpriceticker.toml",
            config_dir / "mempool_apis.toml",
            config_dir / "mempool_serializer.toml",
        ]
    )

    print(
        f"Loaded {len(client.apis)} APIs from {len(client.config_paths)} config files"
    )
    print(f"Loaded {len(client.serializers)} serializers")
    print(f"Loaded {len(client.post_processors)} post-processors\n")

    print("Fetching data from all APIs...")
    results = client.fetch()

    print(f"\nFetch completed at: {client.last_fetch_time}")
    print(f"Total results: {len(results)}\n")

    print("=" * 60)
    print("RESULTS")
    print("=" * 60 + "\n")

    for name, result in results.items():
        status = client.status.get(name, {})
        status_icon = "✓" if status.get("success") else "✗"
        print(f"{status_icon} {name}: {result}")

    print("\n" + "=" * 60)
    print("STATUS SUMMARY")
    print("=" * 60 + "\n")

    successful = client.get_successful_results()
    print(f"Successful: {len(successful)}/{len(results)}")
    print(f"Failed: {len(results) - len(successful)}/{len(results)}")

    print("\n" + "=" * 60)
    print("ACCESSING CACHED RESULTS (no re-fetch)")
    print("=" * 60 + "\n")

    cached_results = client.get_results()
    print(f"Retrieved {len(cached_results)} cached results without fetching")

    if "btc_price_usd" in cached_results:
        print(f"BTC/USD Price: {cached_results['btc_price_usd']}")
    if "block_tip_height" in cached_results:
        print(f"Block Height: {cached_results['block_tip_height']}")


if __name__ == "__main__":
    main()
