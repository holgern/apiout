import tempfile
from pathlib import Path

import pytest

from apiout import ApiClient


@pytest.fixture
def temp_config_file():
    config_content = """
[[apis]]
name = "test_api"
module = "tests.test_api_client"
client_class = "MockClient"
method = "get_data"

[serializers.test_serializer]
[serializers.test_serializer.fields]
value = "value"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(config_content)
        temp_path = Path(f.name)

    yield temp_path
    temp_path.unlink()


@pytest.fixture
def temp_config_file_2():
    config_content = """
[[apis]]
name = "test_api_2"
module = "tests.test_api_client"
client_class = "MockClient"
method = "get_other_data"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(config_content)
        temp_path = Path(f.name)

    yield temp_path
    temp_path.unlink()


class MockClient:
    def get_data(self):
        return {"value": 42}

    def get_other_data(self):
        return {"other": "data"}


def test_api_client_single_config(temp_config_file):
    client = ApiClient(temp_config_file)

    assert len(client.apis) == 1
    assert client.apis[0]["name"] == "test_api"
    assert len(client.serializers) == 1
    assert "test_serializer" in client.serializers


def test_api_client_multiple_configs(temp_config_file, temp_config_file_2):
    client = ApiClient([temp_config_file, temp_config_file_2])

    assert len(client.apis) == 2
    assert len(client.config_paths) == 2


def test_api_client_fetch(temp_config_file):
    client = ApiClient(temp_config_file)

    results = client.fetch()

    assert "test_api" in results
    assert results["test_api"]["value"] == 42
    assert client.last_fetch_time is not None


def test_api_client_get_results(temp_config_file):
    client = ApiClient(temp_config_file)

    client.fetch()
    cached_results = client.get_results()

    assert "test_api" in cached_results
    assert cached_results["test_api"]["value"] == 42


def test_api_client_get_status(temp_config_file):
    client = ApiClient(temp_config_file)

    client.fetch()
    status = client.get_status()

    assert "test_api" in status
    assert status["test_api"]["success"] is True
    assert status["test_api"]["error"] is None
    assert "timestamp" in status["test_api"]


def test_api_client_get_successful_results(temp_config_file):
    client = ApiClient(temp_config_file)

    client.fetch()
    successful = client.get_successful_results()

    assert "test_api" in successful
    assert successful["test_api"]["value"] == 42


def test_api_client_multiple_configs_fetch(temp_config_file, temp_config_file_2):
    client = ApiClient([temp_config_file, temp_config_file_2])

    results = client.fetch()

    assert len(results) == 2
    assert "test_api" in results
    assert "test_api_2" in results
    assert results["test_api"]["value"] == 42
    assert results["test_api_2"]["other"] == "data"
