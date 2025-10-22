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
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional, Union

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

from .serializer import serialize_response


def _substitute_env_vars(value: Any) -> Any:
    """
    Recursively substitute environment variables in configuration values.

    Supports ${VAR_NAME} syntax. If the environment variable is not set,
    the placeholder is left unchanged.

    Args:
        value: Configuration value (can be str, dict, list, or other type)

    Returns:
        Value with environment variables substituted

    Examples:
        >>> os.environ["API_KEY"] = "secret123"
        >>> _substitute_env_vars("Bearer ${API_KEY}")
        'Bearer secret123'
        >>> _substitute_env_vars({"auth": "${API_KEY}", "timeout": 30})
        {'auth': 'secret123', 'timeout': 30}
    """
    if isinstance(value, str):
        # Match ${VAR_NAME} patterns
        def replacer(match):
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))

        return re.sub(r"\$\{([^}]+)\}", replacer, value)
    elif isinstance(value, dict):
        return {k: _substitute_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_substitute_env_vars(item) for item in value]
    else:
        return value


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


def _resolve_client_config(
    api_config: dict[str, Any], client_configs: dict[str, Any]
) -> tuple[Optional[str], str, Optional[str], dict[str, Any], Optional[str]]:
    """
    Resolve client configuration from API config and client configs.

    Returns:
        Tuple of (module_name, client_class_name, client_id, init_params,
        init_method_name)
    """
    module_name = api_config.get("module")
    client_ref = api_config.get("client")

    if client_ref and client_ref in client_configs:
        client_config = client_configs[client_ref]
        if not module_name:
            module_name = client_config.get("module")
        client_class_name = client_config.get("client_class", "Client")
        client_id = client_ref
        init_params = _substitute_env_vars(client_config.get("init_params", {}))
        init_method_name = client_config.get("init_method")
    else:
        client_class_name = api_config.get("client_class", "Client")
        client_id = None
        init_params = _substitute_env_vars(api_config.get("init_params", {}))
        init_method_name = None

    return module_name, client_class_name, client_id, init_params, init_method_name


def _get_or_create_client(
    module: Any,
    client_class_name: str,
    client_id: str | None,
    init_params: dict[str, Any] | None,
    init_method_name: str | None,
    shared_clients: dict[str, Any],
) -> Any:
    """
    Get or create a client instance, using a shared cache.

    Returns:
        Client instance
    """
    cache_key = client_id
    if client_id and init_params:
        cache_key = f"{client_id}:{hash(frozenset(init_params.items()))}"

    if cache_key and cache_key in shared_clients:
        return shared_clients[cache_key]

    client_class = getattr(module, client_class_name)

    if init_params:
        client = client_class(**init_params)
    else:
        client = client_class()

    if init_method_name:
        init_method = getattr(client, init_method_name)
        init_method()

    if cache_key:
        shared_clients[cache_key] = client

    return client


def _prepare_method_arguments(
    method: Any,
    url: str,
    params: dict[str, Any],
    headers: dict[str, Any],
    user_inputs: list[str],
    user_params: dict[str, str],
    user_defaults: dict[str, Any],
) -> tuple[list, dict]:
    """
    Prepare arguments and kwargs for the API method call.

    Returns:
        Tuple of (method_args, method_kwargs)
    """
    sig = inspect.signature(method)
    param_names = list(sig.parameters.keys())
    has_kwargs = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
    )

    method_args = []
    method_kwargs = {}

    if user_inputs:
        for user_input in user_inputs:
            if user_input in user_params:
                value: Any = user_params[user_input]
            elif user_input in user_defaults:
                value = user_defaults[user_input]
            else:
                continue

            try:
                if isinstance(value, str):
                    if value.isdigit():
                        value = int(value)
                    elif value.replace(".", "", 1).isdigit():
                        value = float(value)
            except (AttributeError, ValueError):
                pass

            method_args.append(value)
    elif "params" in param_names:
        method_kwargs["params"] = params
        if url:
            method_args.append(url)
    elif len(param_names) >= 1 and url:
        method_args.append(url)

    # Add params and headers as kwargs if method accepts **kwargs
    if has_kwargs:
        if params:
            method_kwargs["params"] = params
        if headers:
            method_kwargs["headers"] = headers

    return method_args, method_kwargs


def fetch_api_data(
    api_config: dict[str, Any],
    global_serializers: Optional[dict[str, Any]] = None,
    shared_clients: Optional[dict[str, Any]] = None,
    client_configs: Optional[dict[str, Any]] = None,
    user_params: Optional[dict[str, str]] = None,
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
            - user_inputs: List of required user parameter names (optional)
            - user_defaults: Default values for user inputs (optional)
            - serializer: Serializer config or reference (optional)
        global_serializers: Named serializer configurations
        shared_clients: Dict to store/retrieve shared client instances
        client_configs: Dict of named client configurations
        user_params: Dict of user-provided runtime parameters

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
    if user_params is None:
        user_params = {}

    try:
        method_name = api_config.get("method")

        (
            module_name,
            client_class_name,
            client_id,
            init_params,
            init_method_name,
        ) = _resolve_client_config(api_config, client_configs)

        if not module_name:
            return {"error": "No module specified"}

        if not method_name:
            return {"error": "No method specified"}

        user_inputs = api_config.get("user_inputs", [])

        if user_params and init_params:
            for key, value in user_params.items():
                if key in init_params and key not in user_inputs:
                    init_params[key] = value

        module = importlib.import_module(module_name)

        client = _get_or_create_client(
            module,
            client_class_name,
            client_id,
            init_params,
            init_method_name,
            shared_clients,
        )

        method = getattr(client, method_name)

        url = _substitute_env_vars(api_config.get("url", ""))
        params = _substitute_env_vars(api_config.get("params", {}))
        headers = _substitute_env_vars(api_config.get("headers", {}))
        user_defaults = api_config.get("user_defaults", {})

        if user_params and isinstance(params, dict):
            for key, value in user_params.items():
                if key in params or key not in user_inputs:
                    params[key] = value

        if callable(method):
            method_args, method_kwargs = _prepare_method_arguments(
                method, url, params, headers, user_inputs, user_params, user_defaults
            )
            responses = method(*method_args, **method_kwargs)
        else:
            responses = method

        client_ref = api_config.get("client")
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

    def __init__(
        self,
        config_paths: Union[str, Path, list[Union[str, Path]]],
        user_params: Optional[dict[str, str]] = None,
    ):
        """
        Initialize ApiClient with one or more configuration files.

        Args:
            config_paths: Single path or list of paths to TOML configuration files.
                         All configs are loaded and merged during initialization.
            user_params: Optional dict of user-provided runtime parameters
        """
        if isinstance(config_paths, (str, Path)):
            config_paths = [config_paths]

        self.config_paths = [Path(p) for p in config_paths]
        self.user_params = user_params or {}

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

            required_inputs = api_config.get("user_inputs", [])
            if required_inputs:
                user_defaults = api_config.get("user_defaults", {})
                missing = [
                    inp
                    for inp in required_inputs
                    if inp not in self.user_params and inp not in user_defaults
                ]
                if missing:
                    self.status[api_name] = {
                        "success": False,
                        "error": f"Missing required parameter(s): {', '.join(missing)}",
                        "timestamp": time.time(),
                    }
                    continue

            try:
                result = fetch_api_data(
                    api_config,
                    global_serializers=self.serializers,
                    shared_clients=self.shared_clients,
                    client_configs=self.clients,
                    user_params=self.user_params,
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
