"""
API fetching and client management for apiout.

This module provides functionality for:
- Fetching data from API endpoints defined in TOML configurations
- Managing shared client instances across multiple API calls
- Processing post-processors that combine multiple API results
- Serializing API responses according to configuration
"""

import importlib
import inspect
import sys
import time
from pathlib import Path
from typing import Any, Optional, Union

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

from .serializer import serialize_response


def resolve_serializer(
    api_config: dict[str, Any],
    global_serializers: Optional[dict[str, Any]] = None,
    client_ref: Optional[str] = None,
) -> dict[str, Any]:
    """
    Resolve serializer configuration from API config with
    client-scoped namespace support.

    Resolution order:
    1. Inline dict (api_config["serializer"] is dict) - highest priority
    2. Explicit dotted reference (e.g., "client.serializer_name")
    3. Client-scoped lookup (e.g., serializers.{client_ref}.{name})
    4. Global lookup (e.g., serializers.{name})
    5. Empty dict (no serializer found)

    Args:
        api_config: API configuration dict containing optional 'serializer' key
        global_serializers: Optional dict of named serializer configurations
        client_ref: Optional client reference name for scoped serializer lookup

    Returns:
        Resolved serializer configuration dict, or empty dict if none found

    Examples:
        >>> # Global serializer
        >>> api_config = {"serializer": "my_serializer"}
        >>> global_serializers = {"my_serializer": {"fields": {"name": "name"}}}
        >>> resolve_serializer(api_config, global_serializers)
        {'fields': {'name': 'name'}}

        >>> # Client-scoped serializer
        >>> api_config = {"serializer": "data", "client": "btc_price"}
        >>> global_serializers = {"btc_price.data": {"fields": {"value": "usd"}}}
        >>> resolve_serializer(api_config, global_serializers, client_ref="btc_price")
        {'fields': {'value': 'usd'}}

        >>> # Explicit dotted reference
        >>> api_config = {"serializer": "btc_price.data"}
        >>> global_serializers = {"btc_price.data": {"fields": {"value": "usd"}}}
        >>> resolve_serializer(api_config, global_serializers)
        {'fields': {'value': 'usd'}}
    """
    serializer_config: Any = api_config.get("serializer", {})

    # 1. Inline dict - highest priority
    if isinstance(serializer_config, dict):
        return serializer_config

    if not isinstance(serializer_config, str) or not global_serializers:
        return {}

    serializer_name = serializer_config

    # 2. Explicit dotted reference (e.g., "btc_price.price_data")
    if "." in serializer_name:
        return global_serializers.get(serializer_name, {})

    # 3. Client-scoped lookup
    if client_ref:
        client_scoped_name = f"{client_ref}.{serializer_name}"
        if client_scoped_name in global_serializers:
            return global_serializers[client_scoped_name]

    # 4. Global lookup (existing behavior - fallback)
    return global_serializers.get(serializer_name, {})


def fetch_api_data(
    api_config: dict[str, Any],
    global_serializers: Optional[dict[str, Any]] = None,
    shared_clients: Optional[dict[str, Any]] = None,
    client_configs: Optional[dict[str, Any]] = None,
) -> Any:
    """
    Fetch data from an API endpoint based on configuration.

    Dynamically imports a module, instantiates or reuses a client class,
    and calls the specified method. Supports shared client instances when
    using client references.

    Args:
        api_config: API configuration dict with keys:
            - module: Python module to import (required)
            - method: Method name to call on client (required)
            - client: Reference to a client config name (optional)
            - client_class: Class name to instantiate (default: "Client")
            - init_params: Params for client initialization (optional)
            - url: URL parameter to pass to method (optional)
            - params: Additional parameters for method (optional)
            - serializer: Serializer config or reference (optional)
        global_serializers: Named serializer configurations
        shared_clients: Dict to store/retrieve shared client instances
        client_configs: Dict of named client configurations

    Returns:
        Serialized API response data, or error dict if fetch failed

    Example:
        >>> api_config = {
        ...     "module": "requests",
        ...     "client_class": "Session",
        ...     "method": "get",
        ...     "url": "https://api.example.com/data"
        ... }
        >>> result = fetch_api_data(api_config)
    """
    if shared_clients is None:
        shared_clients = {}
    if client_configs is None:
        client_configs = {}

    try:
        module_name = api_config.get("module")
        method_name = api_config.get("method")

        client_ref = api_config.get("client")
        if client_ref and client_ref in client_configs:
            client_config = client_configs[client_ref]
            if not module_name:
                module_name = client_config.get("module")
            client_class_name = client_config.get("client_class", "Client")
            client_id = client_ref
            init_params = client_config.get("init_params", {})
            init_method_name = client_config.get("init_method")
        else:
            client_class_name = api_config.get("client_class", "Client")
            client_id = None
            init_params = api_config.get("init_params", {})
            init_method_name = None

        if not module_name:
            return {"error": "No module specified"}

        if not method_name:
            return {"error": "No method specified"}

        module = importlib.import_module(module_name)

        if client_id and client_id in shared_clients:
            client = shared_clients[client_id]
        else:
            client_class = getattr(module, client_class_name)

            if init_params:
                client = client_class(**init_params)
            else:
                client = client_class()

            if init_method_name:
                init_method = getattr(client, init_method_name)
                init_method()

            if client_id:
                shared_clients[client_id] = client

        method = getattr(client, method_name)

        url = api_config.get("url", "")
        params = api_config.get("params", {})

        sig = inspect.signature(method)
        param_names = list(sig.parameters.keys())

        if "params" in param_names:
            responses = method(url, params=params)
        elif len(param_names) >= 1:
            responses = method(url)
        else:
            responses = method()

        serializer_config = resolve_serializer(
            api_config, global_serializers, client_ref=client_ref
        )
        return serialize_response(responses, serializer_config)

    except ImportError as e:
        return {"error": f"Failed to import module: {e}"}
    except AttributeError as e:
        return {"error": f"Failed to access class or method: {e}"}
    except Exception as e:
        return {"error": f"Failed to fetch data: {e}"}


def process_post_processor(
    post_processor_config: dict[str, Any],
    api_results: dict[str, Any],
    global_serializers: Optional[dict[str, Any]] = None,
) -> Any:
    """
    Process data from multiple APIs using a post-processor class.

    Post-processors combine results from multiple API calls by instantiating
    a class with the API results as arguments, or calling a method on an
    instance with the results.

    Args:
        post_processor_config: Post-processor configuration dict with keys:
            - module: Python module to import (required)
            - class: Class name to instantiate (required)
            - inputs: List of API result names to pass as args (required)
            - method: Method name to call on instance (optional)
            - serializer: Serializer config or reference (optional)
        api_results: Dict of API results by name
        global_serializers: Named serializer configurations

    Returns:
        Serialized post-processor result, or error dict if processing failed

    Example:
        >>> post_processor_config = {
        ...     "module": "mymodule",
        ...     "class": "DataCombiner",
        ...     "inputs": ["api1", "api2"]
        ... }
        >>> api_results = {"api1": {"value": 1}, "api2": {"value": 2}}
        >>> result = process_post_processor(post_processor_config, api_results)
    """
    try:
        module_name = post_processor_config.get("module")
        if not module_name:
            return {"error": "No module specified for post-processor"}

        class_name = post_processor_config.get("class")
        if not class_name:
            return {"error": "No class specified for post-processor"}

        inputs = post_processor_config.get("inputs", [])
        if not inputs:
            return {"error": "No inputs specified for post-processor"}

        for input_name in inputs:
            if input_name not in api_results:
                return {
                    "error": f"Required input '{input_name}' not found in API results"
                }

        module = importlib.import_module(module_name)
        processor_class = getattr(module, class_name)

        input_data = [api_results[input_name] for input_name in inputs]

        method_name = post_processor_config.get("method")
        if method_name:
            processor_instance = processor_class()
            method = getattr(processor_instance, method_name)
            result = method(*input_data)
        else:
            result = processor_class(*input_data)

        serializer_config = resolve_serializer(
            post_processor_config, global_serializers
        )
        return serialize_response(result, serializer_config)

    except ImportError as e:
        return {"error": f"Failed to import post-processor module: {e}"}
    except AttributeError as e:
        return {"error": f"Failed to access post-processor class or method: {e}"}
    except Exception as e:
        return {"error": f"Failed to process post-processor: {e}"}


class ApiClient:
    """
    Stateful API client with configuration management and result caching.

    ApiClient provides a high-level interface for loading API configurations
    from TOML files, fetching data from multiple APIs with shared client
    instances, and caching results for repeated access without re-fetching.

    Supports:
    - Loading single or multiple TOML configuration files
    - Automatic merging of APIs, serializers, and post-processors
    - Shared client instance management via client references
    - Result caching with success/failure tracking
    - Timestamp tracking for each API call

    Attributes:
        config_paths: List of loaded configuration file paths
        apis: List of API configurations from all loaded files
        serializers: Dict of named serializer configurations
        post_processors: List of post-processor configurations
        clients: Dict of named client configurations
        shared_clients: Dict of shared client instances by reference name
        results: Dict of API results by name (cached after fetch)
        status: Dict of status info by name (success, error, timestamp)
        last_fetch_time: Timestamp of the most recent fetch() call

    Example:
        >>> # Single config file
        >>> client = ApiClient("config.toml")
        >>> results = client.fetch()
        >>> cached = client.get_results()
        >>>
        >>> # Multiple config files
        >>> client = ApiClient(["api_config.toml", "serializers.toml"])
        >>> results = client.fetch()
        >>> status = client.get_status()
        >>> successful = client.get_successful_results()
    """

    def __init__(self, config_paths: Union[str, Path, list[Union[str, Path]]]):
        """
        Initialize ApiClient with one or more configuration files.

        Args:
            config_paths: Single path or list of paths to TOML configuration files.
                         All configs are loaded and merged during initialization.
        """
        if isinstance(config_paths, (str, Path)):
            config_paths = [config_paths]

        self.config_paths = [Path(p) for p in config_paths]

        self.apis = []
        self.serializers = {}
        self.post_processors = []
        self.clients = {}

        for config_path in self.config_paths:
            config = self._load_config(config_path)
            self.apis.extend(config.get("apis", []))
            self.serializers.update(config.get("serializers", {}))
            self.post_processors.extend(config.get("post_processors", []))
            self.clients.update(config.get("clients", {}))

        self.shared_clients: dict[str, Any] = {}
        self.results: dict[str, Any] = {}
        self.status: dict[str, dict[str, Any]] = {}
        self.last_fetch_time: Optional[float] = None

    def _load_config(self, config_path: Path) -> dict[str, Any]:
        """
        Load a TOML configuration file.

        Args:
            config_path: Path to TOML file

        Returns:
            Parsed configuration dict
        """
        with open(config_path, "rb") as f:
            return tomllib.load(f)

    def fetch(self) -> dict[str, Any]:
        """
        Fetch data from all configured APIs and post-processors.

        Executes all API calls using shared client instances where configured,
        then runs post-processors on the results. Updates results, status,
        and last_fetch_time attributes.

        Returns:
            Dict mapping API/post-processor names to their results

        Example:
            >>> client = ApiClient("config.toml")
            >>> results = client.fetch()
            >>> print(results["my_api"])
            {'data': 'value'}
        """
        self.last_fetch_time = time.time()

        for api_config in self.apis:
            api_name = api_config.get("name", "unknown")
            try:
                result = fetch_api_data(
                    api_config,
                    global_serializers=self.serializers,
                    shared_clients=self.shared_clients,
                    client_configs=self.clients,
                )

                has_error = isinstance(result, dict) and "error" in result

                self.results[api_name] = result
                self.status[api_name] = {
                    "success": not has_error,
                    "error": result.get("error") if has_error else None,
                    "timestamp": time.time(),
                }
            except Exception as e:
                self.status[api_name] = {
                    "success": False,
                    "error": str(e),
                    "timestamp": time.time(),
                }

        for pp_config in self.post_processors:
            pp_name = pp_config.get("name", "unknown")
            try:
                result = process_post_processor(
                    pp_config, self.results, global_serializers=self.serializers
                )

                has_error = isinstance(result, dict) and "error" in result

                self.results[pp_name] = result
                self.status[pp_name] = {
                    "success": not has_error,
                    "error": result.get("error") if has_error else None,
                    "timestamp": time.time(),
                }
            except Exception as e:
                self.status[pp_name] = {
                    "success": False,
                    "error": str(e),
                    "timestamp": time.time(),
                }

        return self.results

    def get_results(self) -> dict[str, Any]:
        """
        Get cached results without re-fetching.

        Returns:
            Dict of cached results from the last fetch() call

        Example:
            >>> client = ApiClient("config.toml")
            >>> client.fetch()
            >>> cached = client.get_results()  # No network call
        """
        return self.results

    def get_status(self) -> dict[str, dict]:
        """
        Get status information for all APIs and post-processors.

        Returns:
            Dict mapping names to status dicts with keys:
            - success: bool indicating if fetch/processing succeeded
            - error: error message if failed, None otherwise
            - timestamp: Unix timestamp of the operation

        Example:
            >>> client = ApiClient("config.toml")
            >>> client.fetch()
            >>> status = client.get_status()
            >>> print(status["my_api"])
            {'success': True, 'error': None, 'timestamp': 1234567890.123}
        """
        return self.status

    def get_successful_results(self) -> dict[str, Any]:
        """
        Get only results from successful API calls and post-processors.

        Returns:
            Dict containing only results where status['success'] is True

        Example:
            >>> client = ApiClient("config.toml")
            >>> client.fetch()
            >>> successful = client.get_successful_results()
        """
        return {
            name: result
            for name, result in self.results.items()
            if self.status.get(name, {}).get("success", False)
        }
