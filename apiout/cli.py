import json
import os
import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from .fetcher import fetch_api_data, process_post_processor
from .generator import (
    generate_api_toml,
    introspect_and_generate,
    introspect_post_processor_and_generate,
)

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

app = typer.Typer()
console = Console()
err_console = Console(stderr=True)


def _get_config_dir() -> Path:
    """
    Get the apiout configuration directory following XDG Base Directory spec.

    On Unix-like systems: ~/.config/apiout/ (or $XDG_CONFIG_HOME/apiout/)
    On Windows: %LOCALAPPDATA%/apiout/ (or $XDG_CONFIG_HOME/apiout/)

    Returns:
        Path to the configuration directory
    """
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        config_dir = Path(xdg_config_home).expanduser() / "apiout"
    else:
        # Use platform-specific config directory
        if os.name == "nt":  # Windows
            # Use %LOCALAPPDATA% on Windows
            local_app_data = os.environ.get("LOCALAPPDATA")
            if local_app_data:
                config_dir = Path(local_app_data) / "apiout"
            else:
                # Fallback to user profile
                config_dir = Path.home() / "AppData" / "Local" / "apiout"
        else:  # Unix-like (Linux, macOS)
            config_dir = Path.home() / ".config" / "apiout"

    return config_dir


def _load_env_file(env_name: str) -> Path:
    """
    Load an environment file from ~/.config/apiout/

    Args:
        env_name: Name of the environment (e.g., "mempool", "btcprice")

    Returns:
        Path to the environment TOML file

    Raises:
        typer.Exit if the environment file doesn't exist
    """
    config_dir = _get_config_dir()
    env_file = config_dir / f"{env_name}.toml"

    if not env_file.exists():
        err_console.print(
            f"[red]Error: Environment file not found: {env_file}[/red]\n"
            f"[yellow]Hint: Create environment files in {config_dir}/[/yellow]"
        )
        raise typer.Exit(1)

    return env_file


@app.command("gen-serializer")
def gen_serializer_cmd(
    api: str = typer.Option(
        ..., "--api", "-a", help="API or post-processor name from config"
    ),
    config: list[Path] = typer.Option(
        None,
        "-c",
        "--config",
        help="Config file(s) to load (can be specified multiple times)",
    ),
    env: str = typer.Option(None, "-e", "--env", help="Environment name to load"),
) -> None:
    """Generate serializer config by introspecting API response from existing config."""
    if not config and not env:
        err_console.print(
            "[red]Error: Either --config or --env must be specified[/red]"
        )
        raise typer.Exit(1)

    config_paths = list(config) if config else []
    if env:
        env_file = _load_env_file(env)
        config_paths.append(env_file)

    config_data = _load_config_files(config_paths)

    if not config_data.get("apis") and not config_data.get("post_processors"):
        err_console.print(
            "[red]Error: No 'apis' or 'post_processors' section found in config[/red]"
        )
        raise typer.Exit(1)

    api_config = None
    is_post_processor = False

    # Check APIs first
    for api_def in config_data.get("apis", []):
        if api_def.get("name") == api:
            api_config = api_def
            break

    # If not found in APIs, check post-processors
    if not api_config:
        for pp_def in config_data.get("post_processors", []):
            if pp_def.get("name") == api:
                api_config = pp_def
                is_post_processor = True
                break

    if not api_config:
        available_apis = ", ".join(
            a.get("name", "unnamed") for a in config_data.get("apis", [])
        )
        available_pps = ", ".join(
            p.get("name", "unnamed") for p in config_data.get("post_processors", [])
        )
        all_available = []
        if available_apis:
            all_available.append(f"APIs: {available_apis}")
        if available_pps:
            all_available.append(f"Post-processors: {available_pps}")

        err_console.print(
            f"[red]Error: '{api}' not found in config. "
            f"Available: {'; '.join(all_available)}[/red]"
        )
        raise typer.Exit(1)

    try:
        if is_post_processor:
            _generate_post_processor_serializer(api_config, config_data)
        else:
            _generate_api_serializer(api_config, config_data)
    except Exception as e:
        err_console.print(f"[red]Error generating serializer: {e}[/red]")
        raise typer.Exit(1) from e


def _generate_api_serializer(
    api_config: dict[str, Any], config_data: dict[str, Any]
) -> None:
    module = api_config.get("module")
    client_class = api_config.get("client_class", "Client")
    method = api_config.get("method")
    url = api_config.get("url")
    params = api_config.get("params")
    init_params = api_config.get("init_params")
    user_defaults = api_config.get("user_defaults")
    name = api_config["name"]

    client_ref = api_config.get("client")
    if client_ref:
        clients = config_data.get("clients", {})
        if client_ref in clients:
            client_config = clients[client_ref]
            if not module:
                module = client_config.get("module")
            client_class = client_config.get("client_class", "Client")
            init_params = client_config.get("init_params", {})

    if not module or not method:
        err_console.print(
            f"[red]Error: API '{name}' is missing 'module' or 'method'[/red]"
        )
        raise typer.Exit(1)

    result = introspect_and_generate(
        module,
        client_class,
        method,
        url,
        params,
        init_params,
        f"{name}_serializer",
        user_defaults,
    )
    print(result)


def _generate_post_processor_serializer(
    pp_config: dict[str, Any], config_data: dict[str, Any]
) -> None:
    name = pp_config["name"]
    module = pp_config.get("module")
    class_name = pp_config.get("class")
    method = pp_config.get("method", "")
    inputs = pp_config.get("inputs", [])

    if not module or not class_name or not inputs:
        err_console.print(
            f"[red]Error: Post-processor '{name}' is missing 'module', "
            "'class', or 'inputs'[/red]"
        )
        raise typer.Exit(1)

    apis = config_data.get("apis", [])
    clients = config_data.get("clients", {})

    input_configs = []
    for input_name in inputs:
        input_api = next((api for api in apis if api.get("name") == input_name), None)
        if not input_api:
            err_console.print(
                f"[red]Error: Input API '{input_name}' not found in config[/red]"
            )
            raise typer.Exit(1)

        module_name = input_api.get("module")
        client_class_name = input_api.get("client_class", "Client")
        init_params = input_api.get("init_params")

        client_ref = input_api.get("client")
        if client_ref and client_ref in clients:
            client_config = clients[client_ref]
            if not module_name:
                module_name = client_config.get("module")
            client_class_name = client_config.get("client_class", "Client")
            init_params = client_config.get("init_params")

        input_configs.append(
            {
                "module": module_name,
                "client_class": client_class_name,
                "method": input_api.get("method"),
                "url": input_api.get("url"),
                "params": input_api.get("params"),
                "init_params": init_params,
            }
        )

    result = introspect_post_processor_and_generate(
        module, class_name, method, input_configs, f"{name}_serializer"
    )
    print(result)


@app.command("gen-api")
def gen_api_cmd(
    module: str = typer.Option(..., "--module", "-m", help="Python module name"),
    client_class: str = typer.Option(
        "Client", "--client-class", help="Client class name"
    ),
    method: str = typer.Option(..., "--method", help="Method name to call"),
    name: str = typer.Option(..., "--name", "-n", help="API name"),
    client: str = typer.Option(
        None, "--client", help="Client reference name (generates [clients.X] section)"
    ),
    init_params: str = typer.Option(
        None, "--init-params", help="JSON init params dict for client"
    ),
    url: str = typer.Option(None, "--url", "-u", help="API URL (optional)"),
    params: str = typer.Option(
        None, "--params", "-p", help="JSON params dict (optional)"
    ),
    user_inputs: str = typer.Option(
        None, "--user-inputs", help="JSON array of required user input parameter names"
    ),
    user_defaults: str = typer.Option(
        None, "--user-defaults", help="JSON dict of default values for user inputs"
    ),
) -> None:
    init_params_dict = None
    if init_params:
        try:
            init_params_dict = json.loads(init_params)
        except json.JSONDecodeError as e:
            err_console.print(f"[red]Error: Invalid JSON init_params: {e}[/red]")
            raise typer.Exit(1) from e

    params_dict = None
    if params:
        try:
            params_dict = json.loads(params)
        except json.JSONDecodeError as e:
            err_console.print(f"[red]Error: Invalid JSON params: {e}[/red]")
            raise typer.Exit(1) from e

    user_inputs_list = None
    if user_inputs:
        try:
            user_inputs_list = json.loads(user_inputs)
            if not isinstance(user_inputs_list, list):
                err_console.print("[red]Error: user_inputs must be a JSON array[/red]")
                raise typer.Exit(1)
        except json.JSONDecodeError as e:
            err_console.print(f"[red]Error: Invalid JSON user_inputs: {e}[/red]")
            raise typer.Exit(1) from e

    user_defaults_dict = None
    if user_defaults:
        try:
            user_defaults_dict = json.loads(user_defaults)
            if not isinstance(user_defaults_dict, dict):
                err_console.print(
                    "[red]Error: user_defaults must be a JSON object[/red]"
                )
                raise typer.Exit(1)
        except json.JSONDecodeError as e:
            err_console.print(f"[red]Error: Invalid JSON user_defaults: {e}[/red]")
            raise typer.Exit(1) from e

    result = generate_api_toml(
        name=name,
        module_name=module,
        client_class=client_class,
        method_name=method,
        client_ref=client,
        init_params=init_params_dict,
        url=url,
        params=params_dict,
        user_inputs=user_inputs_list,
        user_defaults=user_defaults_dict,
    )

    print(result)


def _flatten_serializers(serializers: dict[str, Any]) -> dict[str, Any]:
    """
    Flatten nested serializer structure to support client-scoped namespaces.

    Converts nested structure like:
        {
            "generic": {"fields": ...},
            "btc_price": {
                "price_data": {"fields": ...},
                "other": {"fields": ...}
            }
        }

    Into flat structure with dotted keys:
        {
            "generic": {"fields": ...},
            "btc_price.price_data": {"fields": ...},
            "btc_price.other": {"fields": ...}
        }

    Args:
        serializers: Dict of serializer configurations (potentially nested)

    Returns:
        Flattened dict with dotted keys for nested serializers
    """
    flat = {}
    for key, value in serializers.items():
        if isinstance(value, dict) and "fields" in value:
            # Top-level serializer (global) - no nesting
            flat[key] = value
        elif isinstance(value, dict):
            # Nested serializers (client-scoped)
            for nested_key, nested_value in value.items():
                if isinstance(nested_value, dict):
                    flat[f"{key}.{nested_key}"] = nested_value
        else:
            # Unexpected format - keep as-is
            flat[key] = value
    return flat


def _load_config_files(config_paths: list[Path]) -> dict[str, Any]:
    config_data: dict[str, Any] = {
        "apis": [],
        "serializers": {},
        "post_processors": [],
        "clients": {},
    }

    for config_path in config_paths:
        if not config_path.exists():
            err_console.print(f"[red]Error: Config file not found: {config_path}[/red]")
            raise typer.Exit(1)

        try:
            with open(config_path, "rb") as f:
                current_config = tomllib.load(f)

                if "apis" in current_config:
                    config_data["apis"].extend(current_config["apis"])

                if "serializers" in current_config:
                    flattened = _flatten_serializers(current_config["serializers"])
                    config_data["serializers"].update(flattened)

                if "post_processors" in current_config:
                    config_data["post_processors"].extend(
                        current_config["post_processors"]
                    )

                if "clients" in current_config:
                    config_data["clients"].update(current_config["clients"])
        except Exception as e:
            err_console.print(
                f"[red]Error reading config file {config_path}: {e}[/red]"
            )
            raise typer.Exit(1) from e

    return config_data


def _load_serializer_files(serializer_paths: list[Path]) -> dict[str, Any]:
    serializers: dict[str, Any] = {}

    for serializers_path in serializer_paths:
        if serializers_path.exists():
            try:
                with open(serializers_path, "rb") as f:
                    serializers_data = tomllib.load(f)
                    flattened = _flatten_serializers(
                        serializers_data.get("serializers", {})
                    )
                    serializers.update(flattened)
            except Exception as e:
                err_console.print(
                    f"[yellow]Warning: Failed to load serializers file "
                    f"{serializers_path}: {e}[/yellow]"
                )

    return serializers


def _process_api(api, all_serializers, err_console, client_configs):
    if "name" not in api:
        err_console.print("[red]Error: Each API must have a 'name' field[/red]")
        raise typer.Exit(1)

    name = api["name"]
    module = api.get("module")
    client_class = api.get("client_class", "Client")
    method = api.get("method")
    url = api.get("url")
    params = api.get("params")
    init_params = api.get("init_params")

    client_ref = api.get("client")
    if client_ref and client_ref in client_configs:
        client_config = client_configs[client_ref]
        if not module:
            module = client_config.get("module")
        client_class = client_config.get("client_class", "Client")
        init_params = client_config.get("init_params", {})

    if not module or not method:
        err_console.print(
            f"[yellow]Warning: Skipping '{name}' - missing module or method[/yellow]"
        )
        return

    err_console.print(f"[blue]Generating serializer for '{name}'...[/blue]")

    try:
        result = introspect_and_generate(
            module, client_class, method, url, params, init_params, f"{name}_serializer"
        )
        all_serializers.append(result)
    except Exception as e:
        err_console.print(
            f"[yellow]Warning: Failed to generate serializer for '{name}': {e}[/yellow]"
        )


@app.command("gen-config")
def generate_from_config_cmd(
    config: list[Path] = typer.Option(
        ...,
        "-c",
        "--config",
        help="Path to TOML configuration file (can be specified multiple times)",
    ),
    output: Path = typer.Option(
        None,
        "-o",
        "--output",
        help="Output file path (prints to stdout if not specified)",
    ),
) -> None:
    config_data = _load_config_files(config)

    if "apis" not in config_data or not config_data["apis"]:
        err_console.print("[red]Error: No 'apis' section found in config file[/red]")
        raise typer.Exit(1)

    apis = config_data["apis"]
    clients = config_data.get("clients", {})
    all_serializers: list[str] = []

    for api in apis:
        _process_api(api, all_serializers, err_console, clients)

    combined_output = "\n\n".join(all_serializers)

    # Process post-processors if any
    post_processors = config_data.get("post_processors", [])
    for pp in post_processors:
        if "name" not in pp:
            err_console.print(
                "[yellow]Warning: Post-processor missing 'name' field[/yellow]"
            )
            continue

        name = pp["name"]
        module = pp.get("module")
        class_name = pp.get("class")
        method = pp.get("method", "")
        inputs = pp.get("inputs", [])

        if not module or not class_name or not inputs:
            err_console.print(
                f"[yellow]Warning: Skipping post-processor '{name}' - "
                "missing module, class, or inputs[/yellow]"
            )
            continue

        err_console.print(
            f"[blue]Generating serializer for post-processor '{name}'...[/blue]"
        )

        # Build input configs by looking up the input APIs
        input_configs = []
        for input_name in inputs:
            # Find the API with this name
            input_api = next(
                (api for api in apis if api.get("name") == input_name), None
            )
            if not input_api:
                err_console.print(
                    f"[yellow]Warning: Input '{input_name}' not found in APIs[/yellow]"
                )
                break

            module_name = input_api.get("module")
            client_class_name = input_api.get("client_class", "Client")
            init_params = input_api.get("init_params")

            client_ref = input_api.get("client")
            if client_ref and client_ref in clients:
                client_config = clients[client_ref]
                if not module_name:
                    module_name = client_config.get("module")
                client_class_name = client_config.get("client_class", "Client")
                init_params = client_config.get("init_params")

            input_configs.append(
                {
                    "module": module_name,
                    "client_class": client_class_name,
                    "method": input_api.get("method"),
                    "url": input_api.get("url"),
                    "params": input_api.get("params"),
                    "init_params": init_params,
                }
            )

        if len(input_configs) != len(inputs):
            continue

        try:
            result = introspect_post_processor_and_generate(
                module, class_name, method, input_configs, f"{name}_serializer"
            )
            all_serializers.append(result)
        except Exception as e:
            err_console.print(
                f"[yellow]Warning: Failed to generate serializer for "
                f"post-processor '{name}': {e}[/yellow]"
            )

    combined_output = "\n\n".join(all_serializers)

    if output:
        try:
            with open(output, "w") as f:
                f.write(combined_output)
            err_console.print(f"[green]Serializers written to {output}[/green]")
        except Exception as e:
            err_console.print(f"[red]Error writing to file: {e}[/red]")
            raise typer.Exit(1) from e
    else:
        console.print(combined_output)


def _parse_params(param_list: list[str]) -> dict[str, str]:
    """
    Parse list of key=value parameter strings into a dict.

    Args:
        param_list: List of strings in format "key=value"

    Returns:
        Dict mapping parameter names to values

    Raises:
        typer.Exit if any parameter is malformed
    """
    params = {}
    for param in param_list:
        if "=" not in param:
            err_console.print(
                f"[red]Error: Invalid parameter format '{param}'. "
                f"Expected format: key=value[/red]"
            )
            raise typer.Exit(1)

        key, value = param.split("=", 1)
        params[key.strip()] = value.strip()

    return params


@app.command("run", help="Run API fetcher with config file")
def main(
    env: list[str] = typer.Option(
        None,
        "-e",
        "--env",
        help="Environment name to load from ~/.config/apiout/ "
        "(can be specified multiple times)",
    ),
    config: list[Path] = typer.Option(
        None,
        "-c",
        "--config",
        help="Path to TOML configuration file (can be specified multiple times)",
    ),
    serializers: list[Path] = typer.Option(
        None,
        "-s",
        "--serializers",
        help="Path to serializers TOML configuration file "
        "(can be specified multiple times)",
    ),
    params: list[str] = typer.Option(
        None,
        "-p",
        "--param",
        help="User parameter in format key=value (can be specified multiple times)",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON format"),
) -> None:
    # Auto-detect JSON input from stdin
    has_stdin = not sys.stdin.isatty()

    if has_stdin and not config and not env:
        # Read from stdin as JSON
        try:
            stdin_data = sys.stdin.read()
            config_data = json.loads(stdin_data)
        except json.JSONDecodeError as e:
            err_console.print(f"[red]Error: Invalid JSON from stdin: {e}[/red]")
            raise typer.Exit(1) from e
    else:
        # Build list of config files from environments and explicit configs
        all_config_files: list[Path] = []

        # Load environment files first
        if env:
            for env_name in env:
                env_file = _load_env_file(env_name)
                all_config_files.append(env_file)

        # Add explicit config files
        if config:
            all_config_files.extend(config)

        # Check if we have any config sources
        if not all_config_files:
            err_console.print(
                "[red]Error: At least one of --env, --config must be provided "
                "(or pipe JSON to stdin)[/red]"
            )
            raise typer.Exit(1)

        config_data = _load_config_files(all_config_files)

    if "apis" not in config_data or not config_data["apis"]:
        err_console.print("[red]Error: No 'apis' section found in config file[/red]")
        raise typer.Exit(1)

    apis = config_data["apis"]
    global_serializers = config_data.get("serializers", {})

    if serializers:
        global_serializers.update(_load_serializer_files(serializers))

    user_params = _parse_params(params) if params else {}

    shared_clients: dict[str, Any] = {}
    client_configs = config_data.get("clients", {})
    results = {}
    for api in apis:
        if "name" not in api:
            err_console.print("[red]Error: Each API must have a 'name' field[/red]")
            raise typer.Exit(1)

        name = api["name"]

        required_inputs = api.get("user_inputs", [])
        if required_inputs:
            user_defaults = api.get("user_defaults", {})
            missing = [
                inp
                for inp in required_inputs
                if inp not in user_params and inp not in user_defaults
            ]
            if missing:
                err_console.print(
                    f"[yellow]Warning: Skipping '{name}' - missing required "
                    f"parameter(s): {', '.join(missing)}[/yellow]"
                )
                continue

        results[name] = fetch_api_data(
            api, global_serializers, shared_clients, client_configs, user_params
        )

    post_processors = config_data.get("post_processors", [])
    for post_processor in post_processors:
        if "name" not in post_processor:
            err_console.print(
                "[red]Error: Each post-processor must have a 'name' field[/red]"
            )
            raise typer.Exit(1)

        name = post_processor["name"]
        results[name] = process_post_processor(
            post_processor, results, global_serializers
        )

    if json_output:
        print(json.dumps(results, indent=2))
    else:
        console.print(results)


if __name__ == "__main__":
    app()
