import json
from collections.abc import Mapping
from typing import Any


def serialize_value(obj: Any) -> Any:
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, (list, tuple)):
        return [serialize_value(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: serialize_value(v) for k, v in obj.items()}
    elif isinstance(obj, Mapping):
        return {k: serialize_value(v) for k, v in obj.items()}
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


def apply_field_mapping(obj: Any, field_config: Any) -> Any:
    if isinstance(field_config, str):
        # Handle simple dot notation paths
        if "." in field_config:
            path_parts = field_config.split(".")
            return traverse_path(obj, path_parts)
        else:
            return call_method_or_attr(obj, field_config)
    if isinstance(field_config, dict):
        result = {}
        # First pass: process all fields to build a complete context
        context = {}
        for key, value in field_config.items():
            if isinstance(value, str):
                if "." in value:
                    context[key] = traverse_path(obj, value.split("."))
                else:
                    context[key] = call_method_or_attr(obj, value)
            elif isinstance(value, dict):
                if "path" in value:
                    # Handle direct path extraction with JSON parsing support
                    path = value["path"]
                    path_parts = path.split(".")
                    parse_json = value.get("parse_json", False)
                    current = traverse_path(obj, path_parts, parse_json)

                    # Handle limit for arrays
                    if isinstance(current, list) and "limit" in value:
                        limit = value["limit"]
                        if isinstance(limit, int) and limit > 0:
                            current = current[:limit]

                    context[key] = current
                elif "method" in value:
                    nested_obj = call_method_or_attr(obj, value["method"])
                    if nested_obj is not None:
                        if "fields" in value:
                            context[key] = apply_field_mapping(
                                nested_obj, value["fields"]
                            )
                        elif "iterate" in value:
                            items = []
                            count_method = value["iterate"].get("count")
                            item_method = value["iterate"].get("item")
                            item_fields = value["iterate"].get("fields", {})
                            limit = value["iterate"].get("limit", None)

                            if count_method and item_method:
                                count = call_method_or_attr(nested_obj, count_method)
                                max_items = (
                                    min(count, limit)
                                    if isinstance(limit, int) and limit > 0
                                    else count
                                )
                                for i in range(max_items):
                                    item_obj = getattr(nested_obj, item_method)(i)
                                    item_data = apply_field_mapping(
                                        item_obj, item_fields
                                    )
                                    items.append(item_data)
                                context[key] = items
                elif "fields" in value:
                    context[key] = apply_field_mapping(obj, value["fields"])
            else:
                # Handle non-string, non-dict values (like True, 200, etc.)
                context[key] = value

        # Second pass: build final result, excluding hidden fields
        for key, value in field_config.items():
            if isinstance(value, dict) and value.get("hidden", False):
                continue  # Skip hidden fields
            result[key] = context[key]

        return result
    else:
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
