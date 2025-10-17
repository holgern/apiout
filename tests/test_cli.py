import pytest
import json
from pathlib import Path
from typer.testing import CliRunner
from apiout.cli import app

runner = CliRunner()


def test_cli_no_config_file():
    result = runner.invoke(app, ["run", "-c", "nonexistent.toml"])
    assert result.exit_code == 1
    assert "Config file not found" in result.stderr


def test_cli_with_invalid_toml(tmp_path):
    config_file = tmp_path / "invalid.toml"
    config_file.write_text("invalid toml content [[[")

    result = runner.invoke(app, ["run", "-c", str(config_file)])
    assert result.exit_code == 1
    assert "Error reading config file" in result.stderr


def test_cli_no_apis_section(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text("[other]\nkey = 'value'")

    result = runner.invoke(app, ["run", "-c", str(config_file)])
    assert result.exit_code == 1
    assert "No 'apis' section found" in result.stderr


def test_cli_api_without_name(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text("[[apis]]\nmodule = 'test'")

    result = runner.invoke(app, ["run", "-c", str(config_file)])
    assert result.exit_code == 1
    assert "must have a 'name' field" in result.stderr


def test_cli_valid_config_with_mock(tmp_path, monkeypatch):
    from unittest.mock import Mock

    mock_fetch = Mock(return_value={"status": "success"})
    monkeypatch.setattr("apiout.cli.fetch_api_data", mock_fetch)

    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[[apis]]
name = "test_api"
module = "test_module"
method = "test_method"
"""
    )

    result = runner.invoke(app, ["run", "-c", str(config_file), "--json"])
    assert result.exit_code == 0

    output = json.loads(result.stdout)
    assert "test_api" in output
    assert output["test_api"] == {"status": "success"}


def test_cli_json_output(tmp_path, monkeypatch):
    from unittest.mock import Mock

    mock_fetch = Mock(return_value={"data": [1, 2, 3]})
    monkeypatch.setattr("apiout.cli.fetch_api_data", mock_fetch)

    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[[apis]]
name = "api1"
module = "mod"
method = "meth"

[[apis]]
name = "api2"
module = "mod2"
method = "meth2"
"""
    )

    result = runner.invoke(app, ["run", "-c", str(config_file), "--json"])
    assert result.exit_code == 0

    output = json.loads(result.stdout)
    assert "api1" in output
    assert "api2" in output
    assert output["api1"] == {"data": [1, 2, 3]}
    assert output["api2"] == {"data": [1, 2, 3]}


def test_cli_with_separate_serializers(tmp_path, monkeypatch):
    from unittest.mock import Mock

    mock_fetch = Mock(return_value={"data": "test"})
    monkeypatch.setattr("apiout.cli.fetch_api_data", mock_fetch)

    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[[apis]]
name = "test_api"
module = "test_module"
method = "test_method"
serializer = "custom"
"""
    )

    serializers_file = tmp_path / "serializers.toml"
    serializers_file.write_text(
        """
[serializers.custom]
[serializers.custom.fields]
value = "Value"
"""
    )

    result = runner.invoke(
        app,
        ["run", "-c", str(config_file), "-s", str(serializers_file), "--json"],
    )
    assert result.exit_code == 0

    mock_fetch.assert_called_once()
    call_args = mock_fetch.call_args[0]
    assert call_args[1] == {"custom": {"fields": {"value": "Value"}}}


def test_cli_with_inline_and_separate_serializers(tmp_path, monkeypatch):
    from unittest.mock import Mock

    mock_fetch = Mock(return_value={"data": "test"})
    monkeypatch.setattr("apiout.cli.fetch_api_data", mock_fetch)

    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[serializers.inline]
[serializers.inline.fields]
inline_field = "InlineValue"

[[apis]]
name = "test_api"
module = "test_module"
method = "test_method"
serializer = "external"
"""
    )

    serializers_file = tmp_path / "serializers.toml"
    serializers_file.write_text(
        """
[serializers.external]
[serializers.external.fields]
external_field = "ExternalValue"
"""
    )

    result = runner.invoke(
        app,
        ["run", "-c", str(config_file), "-s", str(serializers_file), "--json"],
    )
    assert result.exit_code == 0

    mock_fetch.assert_called_once()
    call_args = mock_fetch.call_args[0]
    assert "inline" in call_args[1]
    assert "external" in call_args[1]
