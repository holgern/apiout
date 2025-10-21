from unittest.mock import MagicMock, patch

from apiout.generator import (
    analyze_object,
    generate_serializer_config,
    get_methods_and_attrs,
    introspect_and_generate,
    introspect_post_processor_and_generate,
    is_simple_type,
)


class SimpleObj:
    def __init__(self):
        self.name = "test"
        self.value = 42


class ObjWithMethod:
    def get_data(self):
        return "data"


class NestedObj:
    def __init__(self):
        self.child = SimpleObj()

    def get_child(self):
        return self.child


class CollectionObj:
    def __init__(self):
        self._items = [1, 2, 3]

    def get_length(self):
        return len(self._items)

    def get_item(self, index):
        return self._items[index]


def test_is_simple_type():
    assert is_simple_type("string") is True
    assert is_simple_type(42) is True
    assert is_simple_type(3.14) is True
    assert is_simple_type(True) is True
    assert is_simple_type(None) is True
    assert is_simple_type([]) is False
    assert is_simple_type({}) is False
    assert is_simple_type(SimpleObj()) is False


def test_get_methods_and_attrs():
    obj = ObjWithMethod()
    methods, attrs = get_methods_and_attrs(obj)

    assert "get_data" in methods
    assert "_" not in "".join(attrs)


def test_analyze_simple_object():
    obj = SimpleObj()
    result = analyze_object(obj, max_depth=1)

    assert result["type"] == "object"
    assert result["class"] == "SimpleObj"
    assert "attributes" in result
    assert "name" in result["attributes"]
    assert "value" in result["attributes"]


def test_analyze_object_with_method():
    obj = ObjWithMethod()
    result = analyze_object(obj, max_depth=2)

    assert result["type"] == "object"
    assert "methods" in result
    assert "get_data" in result["methods"]
    assert result["methods"]["get_data"]["type"] == "simple"


def test_analyze_nested_object():
    obj = NestedObj()
    result = analyze_object(obj, max_depth=3)

    assert result["type"] == "object"
    assert "attributes" in result
    assert "child" in result["attributes"]


def test_analyze_collection():
    obj = [1, 2, 3]
    result = analyze_object(obj)

    assert result["type"] == "collection"
    assert "item" in result


def test_analyze_prevents_infinite_recursion():
    obj = SimpleObj()
    obj.self_ref = obj

    result = analyze_object(obj, max_depth=2)

    assert result["type"] == "object"


def test_generate_serializer_config_simple():
    obj = SimpleObj()
    analysis = analyze_object(obj)

    config = generate_serializer_config(analysis)

    assert isinstance(config, dict)
    assert "name" in config or "value" in config


def test_generate_serializer_config_with_method():
    obj = ObjWithMethod()
    analysis = analyze_object(obj, max_depth=2)

    config = generate_serializer_config(analysis)

    assert isinstance(config, dict)


def test_analyze_dict():
    """Test that dictionaries are properly analyzed."""
    data = {
        "name": "test",
        "value": 42,
        "flag": True,
    }
    result = analyze_object(data)

    assert result["type"] == "dict"
    assert "keys" in result
    assert "name" in result["keys"]
    assert "value" in result["keys"]
    assert "flag" in result["keys"]
    assert result["keys"]["name"]["type"] == "simple"
    assert result["keys"]["value"]["type"] == "simple"


def test_analyze_dict_with_same_values():
    """Test that dictionaries with duplicate values (same object ID) work correctly."""
    data = {
        "a": 1,
        "b": 1,
        "c": 1,
    }
    result = analyze_object(data)

    assert result["type"] == "dict"
    assert len(result["keys"]) == 3
    assert all(result["keys"][k]["type"] == "simple" for k in ["a", "b", "c"])


def test_generate_serializer_config_from_dict():
    """Test that serializer configs are generated from dictionaries."""
    data = {
        "firstName": "John",
        "lastName": "Doe",
        "age": 30,
    }
    analysis = analyze_object(data)
    config = generate_serializer_config(analysis)

    assert isinstance(config, dict)
    assert "firstName" in config
    assert "lastName" in config
    assert "age" in config
    assert config["firstName"] == "firstName"
    assert config["lastName"] == "lastName"
    assert config["age"] == "age"


def test_introspect_and_generate_with_dict_response():
    """Test introspecting an API that returns a dictionary."""
    mock_module = MagicMock()
    mock_client_class = MagicMock()
    mock_client = MagicMock()
    mock_method = MagicMock(return_value={"fee": 100, "rate": 1.5})

    mock_client_class.return_value = mock_client
    mock_client.test_method = mock_method
    mock_module.TestClient = mock_client_class

    with patch("apiout.generator.importlib.import_module", return_value=mock_module):
        with patch("apiout.generator.inspect.signature") as mock_sig:
            mock_sig.return_value.parameters.keys.return_value = []

            result = introspect_and_generate(
                "test_module",
                "TestClient",
                "test_method",
                None,
                None,
                None,
                "test_serializer",
            )

    assert "[serializers.test_serializer]" in result
    assert 'fee = "fee"' in result
    assert 'rate = "rate"' in result


def test_introspect_and_generate_with_simple_response():
    """Test introspecting an API that returns a simple type."""
    mock_module = MagicMock()
    mock_client_class = MagicMock()
    mock_client = MagicMock()
    mock_method = MagicMock(return_value="simple string")

    mock_client_class.return_value = mock_client
    mock_client.test_method = mock_method
    mock_module.TestClient = mock_client_class

    with patch("apiout.generator.importlib.import_module", return_value=mock_module):
        with patch("apiout.generator.inspect.signature") as mock_sig:
            mock_sig.return_value.parameters.keys.return_value = []

            result = introspect_and_generate(
                "test_module",
                "TestClient",
                "test_method",
                None,
                None,
                None,
                "test_serializer",
            )

    assert "# Serializer not needed" in result
    assert "simple str" in result


def test_introspect_post_processor_and_generate():
    """Test generating serializers for post-processors."""

    def import_side_effect(name):
        if name == "input_module":
            mock_input_module = MagicMock()
            mock_input_client_class = MagicMock()
            mock_input_client = MagicMock()
            mock_input_method = MagicMock(return_value={"input_data": 123})

            mock_input_client_class.return_value = mock_input_client
            mock_input_client.get_data = mock_input_method
            mock_input_module.InputClient = mock_input_client_class
            return mock_input_module
        elif name == "pp_module":
            mock_pp_module = MagicMock()

            # Create a callable that returns a dict
            def mock_pp_class(*args):
                return {"output": "processed", "score": 99}

            mock_pp_module.PostProcessor = mock_pp_class
            return mock_pp_module
        return MagicMock()

    with patch(
        "apiout.generator.importlib.import_module", side_effect=import_side_effect
    ):
        with patch("apiout.generator.inspect.signature") as mock_sig:
            mock_sig.return_value.parameters.keys.return_value = []

            input_configs = [
                {
                    "module": "input_module",
                    "client_class": "InputClient",
                    "method": "get_data",
                    "url": "",
                    "params": {},
                }
            ]

            result = introspect_post_processor_and_generate(
                "pp_module",
                "PostProcessor",
                "",
                input_configs,
                "pp_serializer",
            )

    assert "[serializers.pp_serializer]" in result
    assert 'output = "output"' in result
    assert 'score = "score"' in result
