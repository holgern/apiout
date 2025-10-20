import json

from typer.testing import CliRunner

from apiout.cli import app

runner = CliRunner()


def test_cli_no_config_file():
    result = runner.invoke(app, ["run", "-c", "nonexistent.toml"])
    assert result.exit_code == 1
    assert "Config file not found" in result.output


def test_cli_with_invalid_toml(tmp_path):
    config_file = tmp_path / "invalid.toml"
    config_file.write_text("invalid toml content [[[")

    result = runner.invoke(app, ["run", "-c", str(config_file)])
    assert result.exit_code == 1
    assert "Error reading config file" in result.output


def test_cli_no_apis_section(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text("[other]\nkey = 'value'")

    result = runner.invoke(app, ["run", "-c", str(config_file)])
    assert result.exit_code == 1
    assert "No 'apis' section found" in result.output


def test_cli_api_without_name(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text("[[apis]]\nmodule = 'test'")

    result = runner.invoke(app, ["run", "-c", str(config_file)])
    assert result.exit_code == 1
    assert "must have a 'name' field" in result.output


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


def test_cli_with_post_processor(tmp_path, monkeypatch):
    from unittest.mock import Mock

    mock_fetch = Mock(side_effect=[{"value": 1}, {"value": 2}])
    mock_process = Mock(return_value={"combined": 3})
    monkeypatch.setattr("apiout.cli.fetch_api_data", mock_fetch)
    monkeypatch.setattr("apiout.cli.process_post_processor", mock_process)

    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[[apis]]
name = "api1"
module = "mod1"
method = "meth1"

[[apis]]
name = "api2"
module = "mod2"
method = "meth2"

[[post_processors]]
name = "processor1"
module = "processor_mod"
class = "ProcessorClass"
inputs = ["api1", "api2"]
"""
    )

    result = runner.invoke(app, ["run", "-c", str(config_file), "--json"])
    assert result.exit_code == 0

    output = json.loads(result.stdout)
    assert "api1" in output
    assert "api2" in output
    assert "processor1" in output
    assert output["processor1"] == {"combined": 3}


def test_cli_post_processor_without_name(tmp_path, monkeypatch):
    from unittest.mock import Mock

    mock_fetch = Mock(return_value={"value": 1})
    monkeypatch.setattr("apiout.cli.fetch_api_data", mock_fetch)

    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[[apis]]
name = "api1"
module = "mod1"
method = "meth1"

[[post_processors]]
module = "processor_mod"
class = "ProcessorClass"
inputs = ["api1"]
"""
    )

    result = runner.invoke(app, ["run", "-c", str(config_file)])
    assert result.exit_code == 1
    assert "must have a 'name' field" in result.output


def test_cli_with_multiple_config_files(tmp_path, monkeypatch):
    from unittest.mock import Mock

    mock_fetch = Mock(return_value={"data": "test"})
    monkeypatch.setattr("apiout.cli.fetch_api_data", mock_fetch)

    config_file1 = tmp_path / "config1.toml"
    config_file1.write_text(
        """
[[apis]]
name = "api1"
module = "mod1"
method = "meth1"
"""
    )

    config_file2 = tmp_path / "config2.toml"
    config_file2.write_text(
        """
[[apis]]
name = "api2"
module = "mod2"
method = "meth2"
"""
    )

    result = runner.invoke(
        app,
        ["run", "-c", str(config_file1), "-c", str(config_file2), "--json"],
    )
    assert result.exit_code == 0

    output = json.loads(result.stdout)
    assert "api1" in output
    assert "api2" in output
    assert mock_fetch.call_count == 2


def test_cli_with_multiple_config_and_serializer_files(tmp_path, monkeypatch):
    from unittest.mock import Mock

    mock_fetch = Mock(return_value={"data": "test"})
    monkeypatch.setattr("apiout.cli.fetch_api_data", mock_fetch)

    config_file1 = tmp_path / "config1.toml"
    config_file1.write_text(
        """
[[apis]]
name = "api1"
module = "mod1"
method = "meth1"
serializer = "ser1"
"""
    )

    config_file2 = tmp_path / "config2.toml"
    config_file2.write_text(
        """
[serializers.ser2]
[serializers.ser2.fields]
field2 = "Value2"

[[apis]]
name = "api2"
module = "mod2"
method = "meth2"
serializer = "ser2"
"""
    )

    serializers_file = tmp_path / "serializers.toml"
    serializers_file.write_text(
        """
[serializers.ser1]
[serializers.ser1.fields]
field1 = "Value1"
"""
    )

    result = runner.invoke(
        app,
        [
            "run",
            "-c",
            str(config_file1),
            "-c",
            str(config_file2),
            "-s",
            str(serializers_file),
            "--json",
        ],
    )
    assert result.exit_code == 0

    output = json.loads(result.stdout)
    assert "api1" in output
    assert "api2" in output
    assert mock_fetch.call_count == 2

    calls = mock_fetch.call_args_list
    serializers_arg = calls[0][0][1]
    assert "ser1" in serializers_arg
    assert "ser2" in serializers_arg
