from unittest.mock import MagicMock, patch

from apiout.fetcher import process_post_processor


def test_process_post_processor_no_module():
    post_processor_config = {"name": "test"}
    api_results = {}
    result = process_post_processor(post_processor_config, api_results)
    assert "error" in result
    assert "No module specified" in result["error"]


def test_process_post_processor_no_class():
    post_processor_config = {"name": "test", "module": "test_module"}
    api_results = {}
    result = process_post_processor(post_processor_config, api_results)
    assert "error" in result
    assert "No class specified" in result["error"]


def test_process_post_processor_no_inputs():
    post_processor_config = {
        "name": "test",
        "module": "test_module",
        "class": "TestClass",
    }
    api_results = {}
    result = process_post_processor(post_processor_config, api_results)
    assert "error" in result
    assert "No inputs specified" in result["error"]


def test_process_post_processor_missing_input():
    post_processor_config = {
        "name": "test",
        "module": "test_module",
        "class": "TestClass",
        "inputs": ["api1", "api2"],
    }
    api_results = {"api1": {"data": "value1"}}
    result = process_post_processor(post_processor_config, api_results)
    assert "error" in result
    assert "api2" in result["error"]


def test_process_post_processor_success():
    class MockProcessor:
        def __init__(self, data1, data2):
            self.result = {"combined": f"{data1}-{data2}"}

    mock_module = MagicMock()
    mock_module.MockProcessor = MockProcessor

    post_processor_config = {
        "name": "test",
        "module": "test_module",
        "class": "MockProcessor",
        "inputs": ["api1", "api2"],
    }
    api_results = {"api1": "value1", "api2": "value2"}

    with patch("apiout.fetcher.importlib.import_module", return_value=mock_module):
        result = process_post_processor(post_processor_config, api_results)
        assert "error" not in result
        assert result == {"result": {"combined": "value1-value2"}}


def test_process_post_processor_with_method():
    class MockProcessor:
        def process(self, data1, data2):
            return {"combined": f"{data1}-{data2}"}

    mock_module = MagicMock()
    mock_module.MockProcessor = MockProcessor

    post_processor_config = {
        "name": "test",
        "module": "test_module",
        "class": "MockProcessor",
        "method": "process",
        "inputs": ["api1", "api2"],
    }
    api_results = {"api1": "value1", "api2": "value2"}

    with patch("apiout.fetcher.importlib.import_module", return_value=mock_module):
        result = process_post_processor(post_processor_config, api_results)
        assert "error" not in result
        assert result == {"combined": "value1-value2"}


def test_process_post_processor_with_serializer():
    class MockData:
        def __init__(self):
            self.value = 42
            self.name = "test"

    class MockProcessor:
        def __init__(self, data1, data2):
            self.data = MockData()
            self.value = 42
            self.name = "test"

    mock_module = MagicMock()
    mock_module.MockProcessor = MockProcessor

    post_processor_config = {
        "name": "test",
        "module": "test_module",
        "class": "MockProcessor",
        "inputs": ["api1", "api2"],
        "serializer": {
            "fields": {
                "value": "value",
                "name": "name",
            }
        },
    }
    api_results = {"api1": "value1", "api2": "value2"}

    with patch("apiout.fetcher.importlib.import_module", return_value=mock_module):
        result = process_post_processor(post_processor_config, api_results)
        assert "error" not in result
        assert result == [{"value": 42, "name": "test"}]


def test_process_post_processor_import_error():
    post_processor_config = {
        "name": "test",
        "module": "nonexistent_module",
        "class": "TestClass",
        "inputs": ["api1"],
    }
    api_results = {"api1": "value1"}

    result = process_post_processor(post_processor_config, api_results)
    assert "error" in result
    assert "Failed to import post-processor module" in result["error"]


def test_process_post_processor_attribute_error():
    mock_module = MagicMock()
    del mock_module.NonExistentClass

    post_processor_config = {
        "name": "test",
        "module": "test_module",
        "class": "NonExistentClass",
        "inputs": ["api1"],
    }
    api_results = {"api1": "value1"}

    with patch("apiout.fetcher.importlib.import_module", return_value=mock_module):
        result = process_post_processor(post_processor_config, api_results)
        assert "error" in result
        assert "Failed to access post-processor class or method" in result["error"]
