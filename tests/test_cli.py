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


def test_gen_api_with_client_ref():
    result = runner.invoke(
        app,
        [
            "gen-api",
            "--module",
            "pymempool",
            "--client-class",
            "MempoolAPI",
            "--client",
            "mempool",
            "--method",
            "get_block_tip_hash",
            "--name",
            "block_tip_hash",
        ],
    )
    assert result.exit_code == 0
    assert "[clients.mempool]" in result.stdout
    assert 'module = "pymempool"' in result.stdout
    assert 'client_class = "MempoolAPI"' in result.stdout
    assert "[[apis]]" in result.stdout
    assert 'name = "block_tip_hash"' in result.stdout
    assert 'client = "mempool"' in result.stdout
    assert 'method = "get_block_tip_hash"' in result.stdout


def test_gen_api_without_client_ref():
    result = runner.invoke(
        app,
        [
            "gen-api",
            "--module",
            "pymempool",
            "--client-class",
            "MempoolAPI",
            "--method",
            "get_block_tip_hash",
            "--name",
            "block_tip_hash",
        ],
    )
    assert result.exit_code == 0
    assert "[clients." not in result.stdout
    assert "[[apis]]" in result.stdout
    assert 'name = "block_tip_hash"' in result.stdout
    assert 'module = "pymempool"' in result.stdout
    assert 'client_class = "MempoolAPI"' in result.stdout
    assert 'method = "get_block_tip_hash"' in result.stdout


def test_gen_api_with_init_params():
    result = runner.invoke(
        app,
        [
            "gen-api",
            "--module",
            "pymempool",
            "--client-class",
            "MempoolAPI",
            "--client",
            "mempool",
            "--method",
            "get_block_tip_hash",
            "--name",
            "block_tip_hash",
            "--init-params",
            '{"api_base_url": "https://mempool.space/api/"}',
        ],
    )
    assert result.exit_code == 0
    assert "[clients.mempool]" in result.stdout
    assert (
        'init_params = {"api_base_url": "https://mempool.space/api/"}' in result.stdout
    )


def test_gen_api_with_user_inputs():
    result = runner.invoke(
        app,
        [
            "gen-api",
            "--module",
            "pymempool",
            "--client-class",
            "MempoolAPI",
            "--client",
            "mempool",
            "--method",
            "get_block_feerates",
            "--name",
            "block_feerates",
            "--user-inputs",
            '["time_period"]',
            "--user-defaults",
            '{"time_period": "24h"}',
        ],
    )
    assert result.exit_code == 0
    assert 'user_inputs = ["time_period"]' in result.stdout
    assert 'user_defaults = {"time_period": "24h"}' in result.stdout


def test_gen_api_with_invalid_init_params():
    result = runner.invoke(
        app,
        [
            "gen-api",
            "--module",
            "pymempool",
            "--client-class",
            "MempoolAPI",
            "--client",
            "mempool",
            "--method",
            "get_block_tip_hash",
            "--name",
            "block_tip_hash",
            "--init-params",
            "invalid json",
        ],
    )
    assert result.exit_code == 1
    assert "Invalid JSON init_params" in result.output


def test_gen_api_with_url_and_params():
    result = runner.invoke(
        app,
        [
            "gen-api",
            "--module",
            "openmeteo_requests",
            "--client-class",
            "Client",
            "--method",
            "weather_api",
            "--name",
            "berlin_weather",
            "--url",
            "https://api.open-meteo.com/v1/forecast",
            "--params",
            '{"latitude": 52.52, "longitude": 13.41}',
        ],
    )
    assert result.exit_code == 0
    assert 'url = "https://api.open-meteo.com/v1/forecast"' in result.stdout
    assert "[apis.params]" in result.stdout
    assert "latitude = 52.52" in result.stdout
    assert "longitude = 13.41" in result.stdout


def test_gen_serializer_requires_config_or_env():
    result = runner.invoke(app, ["gen-serializer", "--api", "test_api"])
    assert result.exit_code == 1
    assert "Either --config or --env must be specified" in result.output


def test_gen_serializer_with_config(tmp_path, monkeypatch):
    from unittest.mock import Mock

    mock_introspect = Mock(
        return_value="[serializers.test_api_serializer]\n[serializers.test_api_serializer.fields]\nvalue = 'data'"
    )
    monkeypatch.setattr("apiout.cli.introspect_and_generate", mock_introspect)

    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[[apis]]
name = "test_api"
module = "test_module"
client_class = "TestClient"
method = "get_data"
"""
    )

    result = runner.invoke(
        app, ["gen-serializer", "--config", str(config_file), "--api", "test_api"]
    )
    assert result.exit_code == 0
    assert "[serializers.test_api_serializer]" in result.stdout
    mock_introspect.assert_called_once_with(
        "test_module",
        "TestClient",
        "get_data",
        None,
        None,
        None,
        "test_api_serializer",
        None,
    )


def test_gen_serializer_with_client_ref(tmp_path, monkeypatch):
    from unittest.mock import Mock

    mock_introspect = Mock(
        return_value="[serializers.mempool_api_serializer]\n[serializers.mempool_api_serializer.fields]\nhash = 'hash'"
    )
    monkeypatch.setattr("apiout.cli.introspect_and_generate", mock_introspect)

    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[clients.mempool]
module = "pymempool"
client_class = "MempoolAPI"
init_params = {api_base_url = "https://mempool.space/api/"}

[[apis]]
name = "mempool_api"
client = "mempool"
method = "get_block_tip_hash"
"""
    )

    result = runner.invoke(
        app, ["gen-serializer", "--config", str(config_file), "--api", "mempool_api"]
    )
    assert result.exit_code == 0
    assert "[serializers.mempool_api_serializer]" in result.stdout
    mock_introspect.assert_called_once_with(
        "pymempool",
        "MempoolAPI",
        "get_block_tip_hash",
        None,
        None,
        {"api_base_url": "https://mempool.space/api/"},
        "mempool_api_serializer",
        None,
    )


def test_gen_serializer_api_not_found(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[[apis]]
name = "other_api"
module = "test"
method = "test"
"""
    )

    result = runner.invoke(
        app, ["gen-serializer", "--config", str(config_file), "--api", "missing_api"]
    )
    assert result.exit_code == 1
    assert "API 'missing_api' not found" in result.output
    assert "Available APIs: other_api" in result.output


def test_gen_serializer_missing_module_or_method(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[[apis]]
name = "incomplete_api"
module = "test_module"
"""
    )

    result = runner.invoke(
        app,
        ["gen-serializer", "--config", str(config_file), "--api", "incomplete_api"],
    )
    assert result.exit_code == 1
    assert "missing required 'module' or 'method' field" in result.output


def test_gen_serializer_no_apis_section(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text("[other]\nkey = 'value'")

    result = runner.invoke(
        app, ["gen-serializer", "--config", str(config_file), "--api", "test"]
    )
    assert result.exit_code == 1
    assert "No 'apis' section found" in result.output


def test_gen_serializer_with_user_defaults(tmp_path, monkeypatch):
    from unittest.mock import Mock

    mock_introspect = Mock(
        return_value="[serializers.test_api_serializer]\n[serializers.test_api_serializer.fields]\nvalue = 'data'"
    )
    monkeypatch.setattr("apiout.cli.introspect_and_generate", mock_introspect)

    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[[apis]]
name = "test_api"
module = "test_module"
client_class = "TestClient"
method = "get_data"
user_inputs = ["time_period"]
user_defaults = {time_period = "24h"}
"""
    )

    result = runner.invoke(
        app, ["gen-serializer", "--config", str(config_file), "--api", "test_api"]
    )
    assert result.exit_code == 0
    assert "[serializers.test_api_serializer]" in result.stdout
    mock_introspect.assert_called_once_with(
        "test_module",
        "TestClient",
        "get_data",
        None,
        None,
        None,
        "test_api_serializer",
        {"time_period": "24h"},
    )
