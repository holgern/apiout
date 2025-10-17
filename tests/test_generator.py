from apiout.generator import (
    analyze_object,
    generate_serializer_config,
    get_methods_and_attrs,
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
