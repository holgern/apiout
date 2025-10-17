import json
from typing import Any


def serialize_value(obj: Any) -> Any:
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, (list, tuple)):
        return [serialize_value(item) for item in obj]
    elif isinstance(obj, dict):
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
    attr = getattr(obj, name)
    if callable(attr):
        result = attr()
        if hasattr(result, "tolist"):
            return result.tolist()
        return result
    return attr


def apply_field_mapping(obj: Any, field_config: Any) -> Any:
    if isinstance(field_config, str):
        return call_method_or_attr(obj, field_config)
    if isinstance(field_config, dict):
        result = {}
        for key, value in field_config.items():
            if isinstance(value, str):
                result[key] = call_method_or_attr(obj, value)
            elif isinstance(value, dict):
                if "method" in value:
                    nested_obj = call_method_or_attr(obj, value["method"])
                    if nested_obj is not None:
                        if "fields" in value:
                            result[key] = apply_field_mapping(
                                nested_obj, value["fields"]
                            )
                        elif "iterate" in value:
                            items = []
                            count_method = value["iterate"].get("count")
                            item_method = value["iterate"].get("item")
                            item_fields = value["iterate"].get("fields", {})

                            if count_method and item_method:
                                count = call_method_or_attr(nested_obj, count_method)
                                for i in range(count):
                                    item_obj = getattr(nested_obj, item_method)(i)
                                    item_data = apply_field_mapping(
                                        item_obj, item_fields
                                    )
                                    items.append(item_data)
                                result[key] = items
                        else:
                            result[key] = serialize_value(nested_obj)
                elif "iterate" in value:
                    items = []
                    count_method = value["iterate"].get("count")
                    item_method = value["iterate"].get("item")
                    item_fields = value["iterate"].get("fields", {})

                    if count_method and item_method:
                        count = call_method_or_attr(obj, count_method)
                        for i in range(count):
                            item_obj = getattr(obj, item_method)(i)
                            item_data = apply_field_mapping(item_obj, item_fields)
                            items.append(item_data)
                        result[key] = items
                elif "fields" in value:
                    result[key] = apply_field_mapping(obj, value["fields"])
        return result
    else:
        return serialize_value(obj)


def apply_config_serializer(responses: Any, serializer_config: dict[str, Any]) -> Any:
    if not isinstance(responses, list):
        responses = [responses]

    results = []
    for response in responses:
        if "fields" in serializer_config:
            result = apply_field_mapping(response, serializer_config["fields"])
            results.append(result)
        else:
            results.append(serialize_value(response))

    return results


def serialize_response(responses: Any, serializer_config: dict[str, Any]) -> Any:
    if serializer_config:
        return apply_config_serializer(responses, serializer_config)
    else:
        if isinstance(responses, list):
            return [serialize_value(r) for r in responses]
        else:
            return serialize_value(responses)
