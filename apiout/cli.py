import json
import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from .fetcher import fetch_api_data, process_post_processor
from .generator import introspect_and_generate, introspect_post_processor_and_generate

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

app = typer.Typer()
console = Console()
err_console = Console(stderr=True)


@app.command("generate")
def generate_cmd(
    module: str = typer.Option(..., "--module", "-m", help="Python module name"),
    client_class: str = typer.Option(
        "Client", "--client-class", "-c", help="Client class name"
    ),
    method: str = typer.Option(..., "--method", help="Method name to call"),
    url: str = typer.Option(..., "--url", "-u", help="API URL"),
    params: str = typer.Option("{}", "--params", "-p", help="JSON params dict"),
    name: str = typer.Option("generated", "--name", "-n", help="Serializer name"),
) -> None:
    try:
        params_dict = json.loads(params)
    except json.JSONDecodeError as e:
        err_console.print(f"[red]Error: Invalid JSON params: {e}[/red]")
        raise typer.Exit(1) from e

    result = introspect_and_generate(
        module, client_class, method, url, params_dict, name
    )

    console.print(result)


def _load_config_files(config_paths: list[Path]) -> dict[str, Any]:
    config_data: dict[str, Any] = {
        "apis": [],
        "serializers": {},
        "post_processors": [],
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
                    config_data["serializers"].update(current_config["serializers"])

                if "post_processors" in current_config:
                    config_data["post_processors"].extend(
                        current_config["post_processors"]
                    )
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
                    serializers.update(serializers_data.get("serializers", {}))
            except Exception as e:
                err_console.print(
                    f"[yellow]Warning: Failed to load serializers file "
                    f"{serializers_path}: {e}[/yellow]"
                )

    return serializers


def _process_api(api, all_serializers, err_console):
    if "name" not in api:
        err_console.print("[red]Error: Each API must have a 'name' field[/red]")
        raise typer.Exit(1)

    name = api["name"]
    module = api.get("module")
    client_class = api.get("client_class", "Client")
    method = api.get("method")
    url = api.get("url", "")
    params = api.get("params", {})

    if not module or not method:
        err_console.print(
            f"[yellow]Warning: Skipping '{name}' - missing module or method[/yellow]"
        )
        return

    err_console.print(f"[blue]Generating serializer for '{name}'...[/blue]")

    try:
        result = introspect_and_generate(
            module, client_class, method, url, params, f"{name}_serializer"
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
    all_serializers: list[str] = []

    for api in apis:
        _process_api(api, all_serializers, err_console)

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

            input_configs.append(
                {
                    "module": input_api.get("module"),
                    "client_class": input_api.get("client_class", "Client"),
                    "method": input_api.get("method"),
                    "url": input_api.get("url", ""),
                    "params": input_api.get("params", {}),
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


@app.command("run", help="Run API fetcher with config file")
def main(
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
    json_output: bool = typer.Option(False, "--json", help="Output as JSON format"),
) -> None:
    # Auto-detect JSON input from stdin
    has_stdin = not sys.stdin.isatty()

    if has_stdin and not config:
        # Read from stdin as JSON
        try:
            stdin_data = sys.stdin.read()
            config_data = json.loads(stdin_data)
        except json.JSONDecodeError as e:
            err_console.print(f"[red]Error: Invalid JSON from stdin: {e}[/red]")
            raise typer.Exit(1) from e
    else:
        if not config:
            err_console.print(
                "[red]Error: --config must be provided (or pipe JSON to stdin)[/red]"
            )
            raise typer.Exit(1)

        config_data = _load_config_files(config)

    if "apis" not in config_data or not config_data["apis"]:
        err_console.print("[red]Error: No 'apis' section found in config file[/red]")
        raise typer.Exit(1)

    apis = config_data["apis"]
    global_serializers = config_data.get("serializers", {})

    if serializers:
        global_serializers.update(_load_serializer_files(serializers))

    shared_clients: dict[str, Any] = {}
    results = {}
    for api in apis:
        if "name" not in api:
            err_console.print("[red]Error: Each API must have a 'name' field[/red]")
            raise typer.Exit(1)

        name = api["name"]
        results[name] = fetch_api_data(api, global_serializers, shared_clients)

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
