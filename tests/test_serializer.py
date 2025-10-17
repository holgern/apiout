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
    assert result == [{"n": "test"}]


def test_serialize_response_with_config_and_list():
    objs = [MockObject(name="a"), MockObject(name="b")]
    config = {"fields": {"n": "name"}}
    result = serialize_response(objs, config)
    assert result == [{"n": "a"}, {"n": "b"}]
