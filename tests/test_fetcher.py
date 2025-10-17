from unittest.mock import Mock, patch

from apiout.fetcher import fetch_api_data, resolve_serializer


class MockClient:
    def api_method(self, url, params=None):
        return {"url": url, "params": params}


def test_fetch_api_data_no_module():
    config = {}
    result = fetch_api_data(config)
    assert result == {"error": "No module specified"}


def test_fetch_api_data_no_method():
    config = {"module": "sys"}
    result = fetch_api_data(config)
    assert result == {"error": "No method specified"}


def test_fetch_api_data_import_error():
    config = {"module": "nonexistent_module", "method": "test"}
    result = fetch_api_data(config)
    assert "error" in result
    assert "Failed to import module" in result["error"]


@patch("apiout.fetcher.importlib.import_module")
def test_fetch_api_data_success(mock_import):
    mock_module = Mock()
    mock_client = MockClient()
    mock_module.Client = Mock(return_value=mock_client)
    mock_import.return_value = mock_module

    config = {
        "module": "test_module",
        "client_class": "Client",
        "method": "api_method",
        "url": "https://example.com",
        "params": {"key": "value"},
    }

    result = fetch_api_data(config)

    assert "url" in result or isinstance(result, list)
    mock_import.assert_called_once_with("test_module")


@patch("apiout.fetcher.importlib.import_module")
def test_fetch_api_data_with_serializer(mock_import):
    mock_response = Mock()
    mock_response.get_value = Mock(return_value=42)

    mock_client = Mock()
    mock_client.api_method = Mock(return_value=mock_response)

    mock_module = Mock()
    mock_module.Client = Mock(return_value=mock_client)
    mock_import.return_value = mock_module

    config = {
        "module": "test_module",
        "client_class": "Client",
        "method": "api_method",
        "url": "https://example.com",
        "params": {},
        "serializer": {"fields": {"value": "get_value"}},
    }

    result = fetch_api_data(config)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == {"value": 42}


@patch("apiout.fetcher.importlib.import_module")
def test_fetch_api_data_attribute_error(mock_import):
    mock_module = Mock()
    mock_module.NonExistentClass = Mock(side_effect=AttributeError("class not found"))
    mock_import.return_value = mock_module

    config = {
        "module": "test_module",
        "client_class": "NonExistentClass",
        "method": "api_method",
    }

    result = fetch_api_data(config)

    assert "error" in result
    assert "Failed to access class or method" in result["error"]


def test_resolve_serializer_with_string_reference():
    api_config = {"serializer": "openmeteo"}
    global_serializers = {"openmeteo": {"fields": {"lat": "Latitude"}}}

    result = resolve_serializer(api_config, global_serializers)

    assert result == {"fields": {"lat": "Latitude"}}


def test_resolve_serializer_with_dict():
    api_config = {"serializer": {"fields": {"lat": "Latitude"}}}
    global_serializers = {}

    result = resolve_serializer(api_config, global_serializers)

    assert result == {"fields": {"lat": "Latitude"}}


def test_resolve_serializer_no_serializer():
    api_config = {}
    global_serializers = {}

    result = resolve_serializer(api_config, global_serializers)

    assert result == {}


def test_resolve_serializer_string_not_found():
    api_config = {"serializer": "nonexistent"}
    global_serializers = {"openmeteo": {"fields": {}}}

    result = resolve_serializer(api_config, global_serializers)

    assert result == {}
