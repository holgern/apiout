import json
from collections.abc import Mapping

from apiout.serializer import (
    apply_field_mapping,
    call_method_or_attr,
    serialize_response,
    serialize_value,
)


class MockObject:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get_value(self):
        return "method_result"


class MockNumpyArray:
    def __init__(self, data):
        self._data = data

    def tolist(self):
        return self._data


def test_serialize_value_primitives():
    assert serialize_value("hello") == "hello"
    assert serialize_value(42) == 42
    assert serialize_value(3.14) == 3.14
    assert serialize_value(True) is True
    assert serialize_value(None) is None


def test_serialize_value_list():
    assert serialize_value([1, 2, 3]) == [1, 2, 3]
    assert serialize_value(["a", "b"]) == ["a", "b"]


def test_serialize_value_dict():
    assert serialize_value({"a": 1, "b": 2}) == {"a": 1, "b": 2}


def test_serialize_value_object():
    obj = MockObject(name="test", value=42)
    result = serialize_value(obj)
    assert result == {"name": "test", "value": 42}


def test_serialize_value_object_excludes_private():
    obj = MockObject(public="visible", _private="hidden")
    result = serialize_value(obj)
    assert result == {"public": "visible"}
    assert "_private" not in result


def test_call_method_or_attr_with_method():
    obj = MockObject()
    result = call_method_or_attr(obj, "get_value")
    assert result == "method_result"


def test_call_method_or_attr_with_attribute():
    obj = MockObject(name="test")
    result = call_method_or_attr(obj, "name")
    assert result == "test"


def test_call_method_or_attr_with_numpy_array():
    class ObjWithArray:
        def get_array(self):
            return MockNumpyArray([1, 2, 3])

    obj = ObjWithArray()
    result = call_method_or_attr(obj, "get_array")
    assert result == [1, 2, 3]


def test_apply_field_mapping_string():
    obj = MockObject(name="test")
    config = "name"
    result = apply_field_mapping(obj, config)
    assert result == "test"


def test_apply_field_mapping_dict_simple():
    obj = MockObject(name="test", value=42)
    config = {"n": "name", "v": "value"}
    result = apply_field_mapping(obj, config)
    assert result == {"n": "test", "v": 42}


def test_apply_field_mapping_dict_with_method():
    class Parent:
        def get_child(self):
            return MockObject(name="child")

    obj = Parent()
    config = {"child": {"method": "get_child", "fields": {"name": "name"}}}
    result = apply_field_mapping(obj, config)
    assert result == {"child": {"name": "child"}}


def test_apply_field_mapping_dict_with_iterate():
    class Item:
        def __init__(self, value):
            self._value = value

        def get_value(self):
            return self._value

    class Collection:
        def __init__(self):
            self._items = [Item(1), Item(2), Item(3)]

        def get_count(self):
            return len(self._items)

        def get_item(self, index):
            return self._items[index]

    obj = Collection()
    config = {
        "items": {
            "method": "get_count",
            "iterate": {
                "count": "get_count",
                "item": "get_item",
                "fields": {"value": "get_value"},
            },
        }
    }

    class Parent:
        def get_collection(self):
            return obj

    parent = Parent()
    config = {
        "items": {
            "method": "get_collection",
            "iterate": {
                "count": "get_count",
                "item": "get_item",
                "fields": {"value": "get_value"},
            },
        }
    }
    result = apply_field_mapping(parent, config)
    assert result == {"items": [{"value": 1}, {"value": 2}, {"value": 3}]}


def test_serialize_response_without_config():
    obj = MockObject(name="test")
    result = serialize_response(obj, {})
    assert result == {"name": "test"}


def test_serialize_response_with_list():
    objs = [MockObject(name="a"), MockObject(name="b")]
    result = serialize_response(objs, {})
    assert result == [{"name": "a"}, {"name": "b"}]


def test_serialize_response_with_config():
    obj = MockObject(name="test", value=42)
    config = {"fields": {"n": "name"}}
    result = serialize_response(obj, config)
    assert result == {"n": "test"}


def test_serialize_response_with_config_and_list():
    objs = [MockObject(name="a"), MockObject(name="b")]
    config = {"fields": {"n": "name"}}
    result = serialize_response(objs, config)
    assert result == [{"n": "a"}, {"n": "b"}]


def test_apply_field_mapping_dict_keys():
    data = {"fastestFee": 2, "halfHourFee": 1, "hourFee": 1}
    config = {"fastest": "fastestFee", "hour": "hourFee"}
    result = apply_field_mapping(data, config)
    assert result == {"fastest": 2, "hour": 1}
    assert "halfHourFee" not in result


def test_apply_field_mapping_dict_rename():
    data = {"temperature": 15.3, "location": "Berlin", "internal_id": "xyz"}
    config = {"temp": "temperature", "city": "location"}
    result = apply_field_mapping(data, config)
    assert result == {"temp": 15.3, "city": "Berlin"}
    assert "internal_id" not in result


def test_apply_field_mapping_nested_dict():
    data = {
        "current": {"temperature": 15.3, "humidity": 65},
        "location": "Berlin",
    }
    config = {
        "weather": {"method": "current", "fields": {"temp": "temperature"}},
        "city": "location",
    }
    result = apply_field_mapping(data, config)
    assert result == {"weather": {"temp": 15.3}, "city": "Berlin"}


def test_serialize_response_dict_with_config():
    data = {"fastestFee": 2, "halfHourFee": 1, "hourFee": 1, "economyFee": 1}
    config = {"fields": {"fastest": "fastestFee", "economy": "economyFee"}}
    result = serialize_response(data, config)
    assert result == {"fastest": 2, "economy": 1}


def test_call_method_or_attr_with_dict():
    data = {"key1": "value1", "key2": 42}
    assert call_method_or_attr(data, "key1") == "value1"
    assert call_method_or_attr(data, "key2") == 42
    assert call_method_or_attr(data, "missing") is None


class MockMapping(Mapping):
    """Mock Mapping class to test non-dict Mapping objects
    (like CaseInsensitiveDict)."""

    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)


def test_serialize_value_mapping_object():
    """Test that Mapping objects (like requests.structures.CaseInsensitiveDict)
    are serialized."""
    mapping = MockMapping(
        {"Content-Type": "application/json", "Authorization": "Bearer token123"}
    )
    result = serialize_value(mapping)
    assert result == {
        "Content-Type": "application/json",
        "Authorization": "Bearer token123",
    }


def test_call_method_or_attr_with_mapping():
    """Test that Mapping objects work with call_method_or_attr."""
    mapping = MockMapping({"key1": "value1", "key2": 42})
    assert call_method_or_attr(mapping, "key1") == "value1"
    assert call_method_or_attr(mapping, "key2") == 42
    assert call_method_or_attr(mapping, "missing") is None


def test_apply_field_mapping_path_through_attribute_with_json_string():
    class ResponseLike:
        def __init__(self, payload: str):
            self._payload = payload

        @property
        def text(self):
            return self._payload

    payload = json.dumps(
        {
            "results": [
                {"id": "/first/id", "title": "First"},
                {"id": "/second/id", "title": "Second"},
            ]
        }
    )
    obj = ResponseLike(payload)
    config = {
        "first_id": "text.results.0.id",
        "first_result": {"path": "text.results", "limit": 1},
    }

    result = apply_field_mapping(obj, config)

    assert result["first_id"] == "/first/id"
    assert result["first_result"] == [{"id": "/first/id", "title": "First"}]


def test_apply_field_mapping_hidden_field():
    """Test that hidden fields are processed but excluded from output."""

    class ResponseLike:
        def __init__(self, payload: str):
            self._payload = payload

        @property
        def text(self):
            return self._payload

    payload = json.dumps(
        {
            "snippets": [
                {"codeTitle": "Example 1", "relevance": 0.9},
                {"codeTitle": "Example 2", "relevance": 0.8},
            ]
        }
    )
    obj = ResponseLike(payload)
    config = {
        "ok": True,
        "status_code": 200,
        "text": {"path": "text", "parse_json": True, "hidden": True},
        "results": {"path": "text.snippets", "limit": 1},
    }

    result = apply_field_mapping(obj, config)

    # Check that hidden field is not in output
    assert "text" not in result

    # Check that other fields are present
    assert result["ok"] is True
    assert result["status_code"] == 200
    assert "results" in result

    # Check that results can access the parsed text data
    assert result["results"] == [{"codeTitle": "Example 1", "relevance": 0.9}]


def test_apply_field_mapping_hidden_field_without_parse_json():
    """Test hidden field without JSON parsing."""
    obj = {
        "ok": True,
        "status_code": 200,
        "text": "raw text",
        "url": "https://example.com",
    }
    config = {
        "ok": "ok",
        "status_code": "status_code",
        "text": {"path": "text", "hidden": True},
        "url": "url",
    }

    result = apply_field_mapping(obj, config)

    # Check that hidden field is not in output
    assert "text" not in result

    # Check that other fields are present
    assert result["ok"] is True
    assert result["status_code"] == 200
    assert result["url"] == "https://example.com"


def test_apply_field_mapping_multiple_hidden_fields():
    """Test multiple hidden fields."""
    obj = {
        "ok": True,
        "status_code": 200,
        "text": '{"data": "value"}',
        "metadata": '{"internal": "data"}',
        "url": "https://example.com",
    }
    config = {
        "ok": "ok",
        "status_code": "status_code",
        "text": {"path": "text", "parse_json": True, "hidden": True},
        "metadata": {"path": "metadata", "parse_json": True, "hidden": True},
        "url": "url",
    }

    result = apply_field_mapping(obj, config)

    # Check that hidden fields are not in output
    assert "text" not in result
    assert "metadata" not in result

    # Check that visible fields are present
    assert result["ok"] is True
    assert result["status_code"] == 200
    assert result["url"] == "https://example.com"


def test_apply_field_mapping_hidden_field_with_method():
    """Test hidden field with method call."""

    class Parent:
        def __init__(self):
            self.ok = True

        def get_child(self):
            return MockObject(name="child", value=42)

    obj = Parent()
    config = {
        "child": {
            "method": "get_child",
            "fields": {"name": "name", "value": "value"},
            "hidden": True,
        },
        "visible": "ok",
    }

    result = apply_field_mapping(obj, config)

    # Check that hidden field is not in output
    assert "child" not in result

    # Check that visible field is present
    assert result["visible"] is True


def test_apply_field_mapping_parse_json():
    """Test parse_json functionality."""

    class ResponseLike:
        def __init__(self, payload: str):
            self._payload = payload

        @property
        def text(self):
            return self._payload

    payload = json.dumps(
        {
            "snippets": [
                {"codeTitle": "Example 1", "relevance": 0.9},
                {"codeTitle": "Example 2", "relevance": 0.8},
            ]
        }
    )
    obj = ResponseLike(payload)
    config = {
        "raw_text": "text",
        "parsed_text": {"path": "text", "parse_json": True},
        "first_snippet": {"path": "text.snippets", "parse_json": True, "limit": 1},
    }

    result = apply_field_mapping(obj, config)

    # Check raw text is still a string
    assert result["raw_text"] == payload
    assert isinstance(result["raw_text"], str)

    # Check parsed text is a dict
    assert isinstance(result["parsed_text"], dict)
    assert "snippets" in result["parsed_text"]
    assert len(result["parsed_text"]["snippets"]) == 2

    # Check first snippet extraction with parse_json
    assert isinstance(result["first_snippet"], list)
    assert len(result["first_snippet"]) == 1
    assert result["first_snippet"][0]["codeTitle"] == "Example 1"


def test_apply_field_mapping_parse_json_invalid_json():
    """Test parse_json with invalid JSON string."""
    obj = {
        "valid_json": '{"key": "value"}',
        "invalid_json": '{"key": invalid}',
        "plain_text": "just text",
    }
    config = {
        "valid": {"path": "valid_json", "parse_json": True},
        "invalid": {"path": "invalid_json", "parse_json": True},
        "plain": {"path": "plain_text", "parse_json": True},
    }

    result = apply_field_mapping(obj, config)

    # Check valid JSON is parsed
    assert isinstance(result["valid"], dict)
    assert result["valid"]["key"] == "value"

    # Check invalid JSON remains as string (parsing failed gracefully)
    assert isinstance(result["invalid"], str)
    assert result["invalid"] == '{"key": invalid}'

    # Check plain text remains as string
    assert isinstance(result["plain"], str)
    assert result["plain"] == "just text"
