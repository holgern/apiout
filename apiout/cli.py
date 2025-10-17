import json
from pathlib import Path

import typer
from rich.console import Console

from .fetcher import fetch_api_data
from .generator import introspect_and_generate

try:
    import tomllib
except ImportError:
    import tomli as tomllib

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
        raise typer.Exit(1)

    result = introspect_and_generate(
        module, client_class, method, url, params_dict, name
    )

    console.print(result)


@app.command("run", help="Run API fetcher with config file")
def main(
    config: Path = typer.Option(
        ..., "-c", "--config", help="Path to TOML configuration file"
    ),
    serializers: Path = typer.Option(
        None, "-s", "--serializers", help="Path to serializers TOML configuration file"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON format"),
) -> None:
    if not config.exists():
        err_console.print(f"[red]Error: Config file not found: {config}[/red]")
        raise typer.Exit(1)

    try:
        with open(config, "rb") as f:
            config_data = tomllib.load(f)
    except Exception as e:
        err_console.print(f"[red]Error reading config file: {e}[/red]")
        raise typer.Exit(1)

    if "apis" not in config_data or not config_data["apis"]:
        err_console.print("[red]Error: No 'apis' section found in config file[/red]")
        raise typer.Exit(1)

    apis = config_data["apis"]
    global_serializers = config_data.get("serializers", {})

    if serializers and serializers.exists():
        try:
            with open(serializers, "rb") as f:
                serializers_data = tomllib.load(f)
                global_serializers.update(serializers_data.get("serializers", {}))
        except Exception as e:
            err_console.print(
                f"[yellow]Warning: Failed to load serializers file: {e}[/yellow]"
            )

    results = {}
    for api in apis:
        if "name" not in api:
            err_console.print("[red]Error: Each API must have a 'name' field[/red]")
            raise typer.Exit(1)

        name = api["name"]
        results[name] = fetch_api_data(api, global_serializers)

    if json_output:
        print(json.dumps(results, indent=2))
    else:
        console.print(results)


if __name__ == "__main__":
    app()
