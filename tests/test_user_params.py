import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from apiout.cli import _parse_params
from apiout.fetcher import ApiClient, fetch_api_data


class TestParseParams:
    def test_parse_single_param(self):
        result = _parse_params(["key=value"])
        assert result == {"key": "value"}

    def test_parse_multiple_params(self):
        result = _parse_params(["key1=value1", "key2=value2"])
        assert result == {"key1": "value1", "key2": "value2"}

    def test_parse_param_with_equals_in_value(self):
        result = _parse_params(["url=https://example.com?a=1&b=2"])
        assert result == {"url": "https://example.com?a=1&b=2"}

    def test_parse_param_with_spaces(self):
        result = _parse_params(["key = value with spaces"])
        assert result == {"key": "value with spaces"}

    def test_parse_empty_list(self):
        result = _parse_params([])
        assert result == {}

    def test_invalid_param_format(self):
        from typer.testing import CliRunner

        from apiout.cli import app

        runner = CliRunner()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[clients.test]\nmodule = "sys"\n')
            f.write('[[apis]]\nname = "test"\nclient = "test"\nmethod = "exit"\n')
            config_path = f.name

        try:
            result = runner.invoke(
                app, ["run", "-c", config_path, "-p", "invalid_format"]
            )
            assert result.exit_code == 1
            assert "Invalid parameter format" in result.output
        finally:
            Path(config_path).unlink()


class TestFetchApiDataWithUserParams:
    def test_fetch_with_single_user_param(self):
        class MockClient:
            def test_method(self, param1):
                return f"result_{param1}"

        api_config = {
            "module": "sys",
            "client_class": "MockClient",
            "method": "test_method",
            "user_inputs": ["param1"],
        }

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.MockClient = MockClient
            mock_import.return_value = mock_module

            result = fetch_api_data(api_config, user_params={"param1": "test_value"})

            assert result == "result_test_value"

    def test_fetch_with_multiple_user_params(self):
        class MockClient:
            def test_method(self, param1, param2):
                return f"{param1}_{param2}"

        api_config = {
            "module": "sys",
            "client_class": "MockClient",
            "method": "test_method",
            "user_inputs": ["param1", "param2"],
        }

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.MockClient = MockClient
            mock_import.return_value = mock_module

            result = fetch_api_data(
                api_config, user_params={"param1": "foo", "param2": "bar"}
            )

            assert result == "foo_bar"

    def test_fetch_with_integer_coercion(self):
        class MockClient:
            def test_method(self, count):
                return count * 2

        api_config = {
            "module": "sys",
            "client_class": "MockClient",
            "method": "test_method",
            "user_inputs": ["count"],
        }

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.MockClient = MockClient
            mock_import.return_value = mock_module

            result = fetch_api_data(api_config, user_params={"count": "42"})

            assert result == 84

    def test_fetch_with_float_coercion(self):
        class MockClient:
            def test_method(self, value):
                return value + 1.5

        api_config = {
            "module": "sys",
            "client_class": "MockClient",
            "method": "test_method",
            "user_inputs": ["value"],
        }

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.MockClient = MockClient
            mock_import.return_value = mock_module

            result = fetch_api_data(api_config, user_params={"value": "3.5"})

            assert result == 5.0

    def test_fetch_without_user_inputs_unchanged(self):
        class MockClient:
            def test_method(self):
                return "no_params"

        api_config = {
            "module": "sys",
            "client_class": "MockClient",
            "method": "test_method",
        }

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.MockClient = MockClient
            mock_import.return_value = mock_module

            result = fetch_api_data(api_config)

            assert result == "no_params"


class TestApiClientWithUserParams:
    def test_api_client_with_user_params(self):
        class MockClient:
            def test_method(self, param1):
                return f"result_{param1}"

        config_content = """
[clients.test]
module = "sys"
client_class = "MockClient"

[[apis]]
name = "test_api"
client = "test"
method = "test_method"
user_inputs = ["param1"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            with patch("importlib.import_module") as mock_import:
                mock_module = MagicMock()
                mock_module.MockClient = MockClient
                mock_import.return_value = mock_module

                client = ApiClient(config_path, user_params={"param1": "test_value"})
                results = client.fetch()

                assert "test_api" in results
                assert results["test_api"] == "result_test_value"
                assert client.status["test_api"]["success"] is True
        finally:
            Path(config_path).unlink()

    def test_api_client_missing_required_param(self):
        config_content = """
[clients.test]
module = "sys"

[[apis]]
name = "test_api"
client = "test"
method = "test_method"
user_inputs = ["param1"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            client = ApiClient(config_path, user_params={})
            results = client.fetch()

            assert "test_api" not in results
            assert client.status["test_api"]["success"] is False
            assert "Missing required parameter" in client.status["test_api"]["error"]
        finally:
            Path(config_path).unlink()

    def test_api_client_partial_params(self):
        class MockClient:
            def method1(self, param1):
                return f"result1_{param1}"

            def method2(self, param2):
                return f"result2_{param2}"

        config_content = """
[clients.test]
module = "sys"
client_class = "MockClient"

[[apis]]
name = "api1"
client = "test"
method = "method1"
user_inputs = ["param1"]

[[apis]]
name = "api2"
client = "test"
method = "method2"
user_inputs = ["param2"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            with patch("importlib.import_module") as mock_import:
                mock_module = MagicMock()
                mock_module.MockClient = MockClient
                mock_import.return_value = mock_module

                client = ApiClient(config_path, user_params={"param1": "value1"})
                results = client.fetch()

                assert "api1" in results
                assert results["api1"] == "result1_value1"
                assert "api2" not in results
                assert client.status["api2"]["success"] is False
        finally:
            Path(config_path).unlink()


class TestCliWithUserParams:
    def test_cli_with_param_flag(self):
        from typer.testing import CliRunner

        from apiout.cli import app

        runner = CliRunner()

        class MockClient:
            def test_method(self, param1):
                return {"result": f"value_{param1}"}

        config_content = """
[clients.test]
module = "sys"
client_class = "MockClient"

[[apis]]
name = "test_api"
client = "test"
method = "test_method"
user_inputs = ["param1"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            with patch("importlib.import_module") as mock_import:
                mock_module = MagicMock()
                mock_module.MockClient = MockClient
                mock_import.return_value = mock_module

                result = runner.invoke(
                    app,
                    ["run", "-c", config_path, "-p", "param1=test_value", "--json"],
                )

                assert result.exit_code == 0
                output = json.loads(result.output)
                assert "test_api" in output
                assert output["test_api"]["result"] == "value_test_value"
        finally:
            Path(config_path).unlink()

    def test_cli_with_multiple_param_flags(self):
        from typer.testing import CliRunner

        from apiout.cli import app

        runner = CliRunner()

        class MockClient:
            def test_method(self, param1, param2):
                return {"result": f"{param1}_{param2}"}

        config_content = """
[clients.test]
module = "sys"
client_class = "MockClient"

[[apis]]
name = "test_api"
client = "test"
method = "test_method"
user_inputs = ["param1", "param2"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            with patch("importlib.import_module") as mock_import:
                mock_module = MagicMock()
                mock_module.MockClient = MockClient
                mock_import.return_value = mock_module

                result = runner.invoke(
                    app,
                    [
                        "run",
                        "-c",
                        config_path,
                        "-p",
                        "param1=foo",
                        "-p",
                        "param2=bar",
                        "--json",
                    ],
                )

                assert result.exit_code == 0
                output = json.loads(result.output)
                assert output["test_api"]["result"] == "foo_bar"
        finally:
            Path(config_path).unlink()

    def test_cli_missing_required_param(self):
        from typer.testing import CliRunner

        from apiout.cli import app

        runner = CliRunner()

        config_content = """
[clients.test]
module = "sys"

[[apis]]
name = "test_api"
client = "test"
method = "test_method"
user_inputs = ["param1"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            result = runner.invoke(app, ["run", "-c", config_path, "--json"])

            assert result.exit_code == 0
            assert "Skipping 'test_api'" in result.output
            assert "missing required parameter" in result.output
        finally:
            Path(config_path).unlink()
