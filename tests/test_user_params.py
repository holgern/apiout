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
            "method_params": {"param1": "default_value"},
        }

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.MockClient = MockClient
            mock_import.return_value = mock_module

            result = fetch_api_data(api_config, user_params={})

            assert result == "result_default_value"

    def test_fetch_with_method_params_override(self):
        class MockClient:
            def test_method(self, param1):
                return f"result_{param1}"

        api_config = {
            "module": "sys",
            "client_class": "MockClient",
            "method": "test_method",
            "method_params": {"param1": "default_value"},
        }

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.MockClient = MockClient
            mock_import.return_value = mock_module

            result = fetch_api_data(api_config, user_params={"param1": "override"})

            assert result == "result_override"


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
method_params = {param1 = ""}
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
method_params = {param1 = ""}
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
name = "test_api"
client = "test"
method = "method1"
method_params = {param1 = "default_value"}
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            with patch("importlib.import_module") as mock_import:
                mock_module = MagicMock()
                mock_module.MockClient = MockClient
                mock_import.return_value = mock_module

                client = ApiClient(config_path, user_params={})
                results = client.fetch()

                assert "test_api" in results
                assert results["test_api"] == "result1_default_value"
                assert client.status["test_api"]["success"] is True
        finally:
            Path(config_path).unlink()

    def test_api_client_user_param_overrides_default(self):
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
method_params = {param1 = "default_value"}
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            with patch("importlib.import_module") as mock_import:
                mock_module = MagicMock()
                mock_module.MockClient = MockClient
                mock_import.return_value = mock_module

                client = ApiClient(config_path, user_params={"param1": "override"})
                results = client.fetch()

                assert "test_api" in results
                assert results["test_api"] == "result_override"
                assert client.status["test_api"]["success"] is True
        finally:
            Path(config_path).unlink()


class TestInitParamsOverride:
    def test_user_params_override_init_params(self):
        class MockClient:
            def __init__(self, fiat="EUR", service="default"):
                self.fiat = fiat
                self.service = service

            def get_fiat(self):
                return self.fiat

            def get_service(self):
                return self.service

        api_config = {
            "module": "sys",
            "client_class": "MockClient",
            "method": "get_fiat",
            "init_params": {"fiat": "EUR", "service": "default"},
        }

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.MockClient = MockClient
            mock_import.return_value = mock_module

            result = fetch_api_data(api_config, user_params={"fiat": "USD"})

            assert result == "USD"

    def test_user_params_override_multiple_init_params(self):
        class MockClient:
            def __init__(self, fiat="EUR", days_ago=1, service="coinpaprika"):
                self.fiat = fiat
                self.days_ago = days_ago
                self.service = service

            def get_config(self):
                return {
                    "fiat": self.fiat,
                    "days_ago": self.days_ago,
                    "service": self.service,
                }

        api_config = {
            "module": "sys",
            "client_class": "MockClient",
            "method": "get_config",
            "init_params": {"fiat": "EUR", "days_ago": 1, "service": "coinpaprika"},
        }

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.MockClient = MockClient
            mock_import.return_value = mock_module

            result = fetch_api_data(
                api_config, user_params={"fiat": "USD", "days_ago": "7"}
            )

            assert result["fiat"] == "USD"
            assert result["days_ago"] == "7"
            assert result["service"] == "coinpaprika"

    def test_init_params_not_overridden_by_method_params(self):
        class MockClient:
            def __init__(self, fiat="EUR"):
                self.fiat = fiat

            def test_method(self, topic):
                return {"fiat": self.fiat, "topic": topic}

        api_config = {
            "module": "sys",
            "client_class": "MockClient",
            "method": "test_method",
            "init_params": {"fiat": "EUR"},
            "method_params": {"fiat": None, "topic": "test_topic"},
        }

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.MockClient = MockClient
            mock_import.return_value = mock_module

            result = fetch_api_data(api_config, user_params={"fiat": "USD"})

            assert result["fiat"] == "EUR"

    def test_different_init_params_create_different_clients(self):
        instance_count = {"count": 0}

        class MockClient:
            def __init__(self, fiat="EUR"):
                instance_count["count"] += 1
                self.instance_id = instance_count["count"]
                self.fiat = fiat

            def get_instance_id(self):
                return self.instance_id

        config_content = """
[clients.test]
module = "sys"
client_class = "MockClient"
init_params = {fiat = "EUR"}

[[apis]]
name = "api1"
client = "test"
method = "get_instance_id"

[[apis]]
name = "api2"
client = "test"
method = "get_instance_id"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            with patch("importlib.import_module") as mock_import:
                mock_module = MagicMock()
                mock_module.MockClient = MockClient
                mock_import.return_value = mock_module

                client1 = ApiClient(config_path, user_params={})
                results1 = client1.fetch()

                client2 = ApiClient(config_path, user_params={"fiat": "USD"})
                results2 = client2.fetch()

                assert results1["api1"] == results1["api2"]

                assert results2["api1"] == results2["api2"]

                assert results1["api1"] != results2["api1"]
        finally:
            Path(config_path).unlink()

    def test_same_init_params_reuse_client_cache(self):
        instance_count = {"count": 0}

        class MockClient:
            def __init__(self, fiat="EUR"):
                instance_count["count"] += 1
                self.instance_id = instance_count["count"]

            def get_instance_id(self):
                return self.instance_id

        config_content = """
[clients.test]
module = "sys"
client_class = "MockClient"
init_params = {fiat = "EUR"}

[[apis]]
name = "api1"
client = "test"
method = "get_instance_id"

[[apis]]
name = "api2"
client = "test"
method = "get_instance_id"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            with patch("importlib.import_module") as mock_import:
                mock_module = MagicMock()
                mock_module.MockClient = MockClient
                mock_import.return_value = mock_module

                client = ApiClient(config_path, user_params={})
                results = client.fetch()

                assert results["api1"] == results["api2"]
                assert instance_count["count"] == 1
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
method_params = {param1 = ""}
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
method_params = {param1 = "", param2 = ""}
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
method_params = {param1 = ""}
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
