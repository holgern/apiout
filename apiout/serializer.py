import json
from collections.abc import Mapping
from typing import Any


def serialize_key(key: Any) -> str:
    if isinstance(key, str):
        return key

    isoformat = getattr(key, "isoformat", None)
    if callable(isoformat):
        try:
            return isoformat()
        except Exception:
            pass

    return str(key)


def serialize_value(obj: Any) -> Any:
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, (list, tuple)):
        return [serialize_value(item) for item in obj]
    elif isinstance(obj, dict):
        return {serialize_key(k): serialize_value(v) for k, v in obj.items()}
    elif isinstance(obj, Mapping):
        return {serialize_key(k): serialize_value(v) for k, v in obj.items()}
    elif hasattr(obj, "__dict__") and obj.__dict__:
        result = {}
        for key, value in obj.__dict__.items():
            if not key.startswith("_"):
                result[key] = serialize_value(value)
        return result
    else:
        try:
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            return str(obj)


def call_method_or_attr(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    elif isinstance(obj, Mapping):
        return obj.get(name)

    attr = getattr(obj, name)
    if callable(attr):
        result = attr()
        if hasattr(result, "tolist"):
            return result.tolist()  # type: ignore[union-attr]
        return result
    return attr


def traverse_path(obj: Any, path_parts: list[str], parse_json: bool = False) -> Any:
    current = obj
    idx = 0

    while idx < len(path_parts):
        if current is None:
            return None

        part = path_parts[idx]

        # Auto-parse JSON strings when traversing (only if not explicitly requested)
        if isinstance(current, str) and not parse_json:
            try:
                current = json.loads(current)
                continue
            except (json.JSONDecodeError, TypeError, ValueError):
                return None

        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, Mapping) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit():
            idx_value = int(part)
            if 0 <= idx_value < len(current):
                current = current[idx_value]
            else:
                return None
        else:
            try:
                current = call_method_or_attr(current, part)
            except AttributeError:
                return None

        # Parse JSON if requested after accessing the first part
        if parse_json and idx == 0 and isinstance(current, str):
            try:
                current = json.loads(current)
            except (json.JSONDecodeError, TypeError, ValueError):
                pass  # Keep original string if parsing fails

        idx += 1

    return current


def _resolve_string_field(obj: Any, field_config: str) -> Any:
    if "." in field_config:
        return traverse_path(obj, field_config.split("."))
    return call_method_or_attr(obj, field_config)


def _process_iterate_config(
    nested_obj: Any, iterate_config: dict[str, Any]
) -> list[Any]:
    items: list[Any] = []
    count_method = iterate_config.get("count")
    item_method = iterate_config.get("item")
    item_fields = iterate_config.get("fields", {})
    limit = iterate_config.get("limit")

    if not (count_method and item_method):
        return items

    count = call_method_or_attr(nested_obj, count_method)
    if not isinstance(count, int) or count < 0:
        return items

    max_items = min(count, limit) if isinstance(limit, int) and limit > 0 else count

    getter = getattr(nested_obj, item_method, None)
    if getter is None or not callable(getter):
        return items

    for i in range(max_items):
        item_obj = getter(i)
        items.append(apply_field_mapping(item_obj, item_fields))

    return items


def _resolve_path_config(obj: Any, config: dict[str, Any]) -> Any:
    path_parts = config["path"].split(".")
    parse_json = config.get("parse_json", False)
    current = traverse_path(obj, path_parts, parse_json)

    limit = config.get("limit")
    if isinstance(current, list) and isinstance(limit, int) and limit > 0:
        current = current[:limit]

    item_fields = config.get("item_fields")
    if item_fields and isinstance(current, list):
        current = [apply_field_mapping(item, item_fields) for item in current]

    item_serializer = config.get("item_serializer")
    if item_serializer and isinstance(current, list):
        current = [apply_config_serializer(item, item_serializer) for item in current]

    return current


def _resolve_method_config(obj: Any, config: dict[str, Any]) -> Any:
    nested_obj = call_method_or_attr(obj, config["method"])
    if nested_obj is None:
        return None

    if "fields" in config:
        return apply_field_mapping(nested_obj, config["fields"])

    if "item_fields" in config and isinstance(nested_obj, list):
        item_fields = config["item_fields"]
        return [apply_field_mapping(item, item_fields) for item in nested_obj]

    if "item_serializer" in config and isinstance(nested_obj, list):
        item_serializer = config["item_serializer"]
        return [apply_config_serializer(item, item_serializer) for item in nested_obj]

    if "iterate" in config:
        iterate_config = config["iterate"]
        if isinstance(iterate_config, dict):
            return _process_iterate_config(nested_obj, iterate_config)

    return nested_obj


def _resolve_dict_config(obj: Any, config: dict[str, Any]) -> Any:
    if "path" in config:
        return _resolve_path_config(obj, config)

    if "method" in config:
        return _resolve_method_config(obj, config)

    if "fields" in config:
        return apply_field_mapping(obj, config["fields"])

    return config


def _resolve_mapping_value(obj: Any, value: Any) -> Any:
    if isinstance(value, str):
        return _resolve_string_field(obj, value)

    if isinstance(value, dict):
        return _resolve_dict_config(obj, value)

    return value


def apply_field_mapping(obj: Any, field_config: Any) -> Any:
    if isinstance(field_config, str):
        return _resolve_string_field(obj, field_config)

    if isinstance(field_config, dict):
        context = {
            key: _resolve_mapping_value(obj, value)
            for key, value in field_config.items()
        }

        return {
            key: context[key]
            for key, value in field_config.items()
            if not (isinstance(value, dict) and value.get("hidden", False))
        }

    return serialize_value(obj)


def apply_config_serializer(responses: Any, serializer_config: dict[str, Any]) -> Any:
    is_single = not isinstance(responses, list)
    if is_single:
        responses = [responses]

    results = []
    for response in responses:
        if "fields" in serializer_config:
            result = apply_field_mapping(response, serializer_config["fields"])
            results.append(result)
        else:
            results.append(serialize_value(response))

    return results[0] if is_single else results


def serialize_response(responses: Any, serializer_config: dict[str, Any]) -> Any:
    if serializer_config:
        return apply_config_serializer(responses, serializer_config)
    else:
        if isinstance(responses, list):
            return [serialize_value(r) for r in responses]
        else:
            return serialize_value(responses)
