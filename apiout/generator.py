import importlib
import inspect
from typing import Any, Optional


def is_simple_type(obj: Any) -> bool:
    return isinstance(obj, (str, int, float, bool, type(None)))


def is_collection(obj: Any) -> bool:
    return isinstance(obj, (list, tuple))


def get_methods_and_attrs(obj: Any) -> tuple[list[str], list[str]]:
    methods = []
    attrs = []

    for name in dir(obj):
        if name.startswith("_"):
            continue
        try:
            attr = getattr(obj, name)
            if callable(attr):
                methods.append(name)
            else:
                attrs.append(name)
        except Exception:
            pass

    return methods, attrs


def analyze_object(
    obj: Any,
    max_depth: int = 3,
    current_depth: int = 0,
    visited: Optional[set[int]] = None,
) -> dict[str, Any]:
    if visited is None:
        visited = set()

    if is_simple_type(obj):
        return {"type": "simple", "value_type": type(obj).__name__}

    obj_id = id(obj)
    if obj_id in visited or current_depth >= max_depth:
        return {}

    visited.add(obj_id)

    if is_collection(obj):
        if len(obj) > 0:
            item_analysis = analyze_object(
                obj[0], max_depth, current_depth + 1, visited
            )
            return {"type": "collection", "item": item_analysis}
        return {"type": "collection", "item": {}}

    if isinstance(obj, dict):
        return {
            "type": "dict",
            "keys": {
                k: analyze_object(v, max_depth, current_depth + 1, visited)
                for k, v in obj.items()
            },
        }

    methods, attrs = get_methods_and_attrs(obj)

    result = {
        "type": "object",
        "class": type(obj).__name__,
        "methods": {},
        "attributes": {},
    }

    for method_name in methods:
        try:
            method = getattr(obj, method_name)
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())

            if not params or (len(params) == 1 and params[0] == "self"):
                method_result = method()
                result["methods"][method_name] = analyze_object(  # type: ignore[index]
                    method_result, max_depth, current_depth + 1, visited
                )
            elif len(params) == 1 or (len(params) == 2 and params[0] == "self"):
                result["methods"][method_name] = {  # type: ignore[index]
                    "type": "indexed_method",
                    "note": "Takes index parameter, likely for iteration",
                }
        except Exception as e:
            result["methods"][method_name] = {  # type: ignore[index]
                "type": "error",
                "error": str(e),
            }

    for attr_name in attrs:
        try:
            attr = getattr(obj, attr_name)
            result["attributes"][attr_name] = analyze_object(  # type: ignore[index]
                attr, max_depth, current_depth + 1, visited
            )
        except Exception:
            pass

    return result


def generate_serializer_config(  # noqa: C901
    analysis: dict[str, Any], prefix: str = ""
) -> dict[str, Any]:
    if analysis.get("type") == "simple":
        return {}

    if analysis.get("type") == "collection":
        return {}

    if analysis.get("type") == "dict":
        fields = {}
        for key, value_info in analysis.get("keys", {}).items():
            if value_info.get("type") == "simple":
                fields[key] = key
        return fields

    if analysis.get("type") != "object":
        return {}

    fields = {}

    for method_name, method_info in analysis.get("methods", {}).items():
        if method_info.get("type") == "simple":
            fields[method_name] = method_name

        elif method_info.get("type") == "indexed_method":
            continue

        elif method_info.get("type") == "object":
            method_info.get("class", "")

            if "Length" in method_name or "Count" in method_name:
                continue

            item_method_name = (
                method_name.replace("Current", "")
                .replace("Hourly", "")
                .replace("Daily", "")
            )
            (
                f"{item_method_name}s"
                if not item_method_name.endswith("s")
                else item_method_name
            )

            if any(
                m.get("type") == "indexed_method"
                for m in method_info.get("methods", {}).values()
            ):
                count_method = None
                item_method = None

                for m_name in method_info.get("methods", {}):
                    if "Length" in m_name or "Count" in m_name:
                        count_method = m_name
                    elif method_info["methods"][m_name].get("type") == "indexed_method":
                        item_method = m_name

                if count_method and item_method:
                    item_fields = {}
                    for m_name, m_info in method_info.get("methods", {}).items():
                        if m_info.get("type") == "simple":
                            item_fields[m_name] = m_name

                    fields[method_name] = {
                        "method": method_name,
                        "iterate": {
                            "count": count_method,
                            "item": item_method,
                            "fields": item_fields,
                        },
                    }
                else:
                    nested_config = generate_serializer_config(
                        method_info, f"{prefix}{method_name}."
                    )
                    if nested_config:
                        fields[method_name] = {
                            "method": method_name,
                            "fields": nested_config,
                        }
            else:
                nested_config = generate_serializer_config(
                    method_info, f"{prefix}{method_name}."
                )
                if nested_config:
                    fields[method_name] = {
                        "method": method_name,
                        "fields": nested_config,
                    }

    for attr_name, attr_info in analysis.get("attributes", {}).items():
        if attr_info.get("type") == "simple":
            fields[attr_name] = attr_name

    return fields


def generate_toml_serializer(name: str, fields: dict[str, Any], indent: int = 0) -> str:
    lines = []
    indent_str = "  " * indent

    for key, value in fields.items():
        if isinstance(value, str):
            lines.append(f'{indent_str}{key} = "{value}"')
        elif isinstance(value, dict):
            if "method" in value:
                lines.append(f"\n{indent_str}[{name}.{key}]")
                lines.append(f'{indent_str}method = "{value["method"]}"')

                if "fields" in value:
                    nested_lines = generate_toml_serializer(
                        f"{name}.{key}.fields", value["fields"], 0
                    )
                    lines.append(f"[{name}.{key}.fields]")
                    lines.append(nested_lines)

                if "iterate" in value:
                    iterate = value["iterate"]
                    fields_str = ", ".join(
                        [f'{k} = "{v}"' for k, v in iterate.get("fields", {}).items()]
                    )
                    lines.append(
                        f"[{name}.{key}.fields.variables]\n"
                        f'iterate = {{ count = "{iterate["count"]}", '
                        f'item = "{iterate["item"]}", fields = {{ {fields_str} }} }}'
                    )

    return "\n".join(lines)


def introspect_and_generate(
    module_name: str,
    client_class: str,
    method_name: str,
    url: Optional[str] = None,
    params: Optional[dict[str, Any]] = None,
    init_params: Optional[dict[str, Any]] = None,
    serializer_name: str = "generated",
) -> str:
    try:
        module = importlib.import_module(module_name)
        client_cls = getattr(module, client_class)

        if init_params:
            client = client_cls(**init_params)
        else:
            client = client_cls()

        method = getattr(client, method_name)

        sig = inspect.signature(method)
        method_params = list(sig.parameters.keys())

        if url is not None and "params" in method_params:
            response = method(url, params=params or {})
        elif url is not None and len(method_params) > 0:
            response = method(url)
        else:
            response = method()

        if isinstance(response, list) and len(response) > 0:
            sample = response[0]
        else:
            sample = response

        analysis = analyze_object(sample)

        if analysis.get("type") == "simple":
            vtype = analysis.get("value_type", "value")
            return (
                f"# Serializer not needed: API returns a simple {vtype}, "
                "use auto-serialization"
            )

        fields = generate_serializer_config(analysis)

        toml_output = f"[serializers.{serializer_name}]\n"
        toml_output += f"[serializers.{serializer_name}.fields]\n"

        simple_fields = {k: v for k, v in fields.items() if isinstance(v, str)}
        for key, value in simple_fields.items():
            toml_output += f'{key} = "{value}"\n'

        complex_fields: dict[str, Any] = {
            k: v for k, v in fields.items() if isinstance(v, dict)
        }
        for key, value in complex_fields.items():
            if not isinstance(value, dict):
                continue
            toml_output += f"\n[serializers.{serializer_name}.fields.{key}]\n"
            toml_output += f'method = "{value["method"]}"\n'

            if "fields" in value:
                toml_output += f"[serializers.{serializer_name}.fields.{key}.fields]\n"
                for fk, fv in value["fields"].items():
                    if isinstance(fv, str):
                        toml_output += f'{fk} = "{fv}"\n'
                    elif isinstance(fv, dict) and "iterate" in fv:
                        iterate = fv["iterate"]
                        fields_str = ", ".join(
                            [
                                f'{k} = "{v}"'
                                for k, v in iterate.get("fields", {}).items()
                            ]
                        )
                        toml_output += (
                            f"[serializers.{serializer_name}.fields.{key}."
                            f"fields.variables]\n"
                        )
                        toml_output += (
                            f'iterate = {{ count = "{iterate["count"]}", '
                            f'item = "{iterate["item"]}", '
                            f"fields = {{ {fields_str} }} }}\n"
                        )

            if "iterate" in value:
                iterate = value["iterate"]
                fields_str = ", ".join(
                    [f'{k} = "{v}"' for k, v in iterate.get("fields", {}).items()]
                )
                toml_output += (
                    f"[serializers.{serializer_name}.fields.{key}.fields.variables]\n"
                )
                toml_output += (
                    f'iterate = {{ count = "{iterate["count"]}", '
                    f'item = "{iterate["item"]}", '
                    f"fields = {{ {fields_str} }} }}\n"
                )

        return toml_output

    except Exception as e:
        return f"# Error generating serializer: {e}"


def introspect_post_processor_and_generate(
    module_name: str,
    class_name: str,
    method_name: str,
    input_modules: list[dict[str, Any]],
    serializer_name: str = "generated",
) -> str:
    """
    Generate serializer for a post-processor by calling it with sample data.

    Args:
        module_name: Module containing the post-processor class
        class_name: Post-processor class name
        method_name: Optional method to call on the instance
        input_modules: List of dicts with 'module', 'client_class',
            'method', optional 'init_params', 'url', 'params' keys
        serializer_name: Name for the generated serializer
    """
    try:
        # Fetch sample data from all input APIs
        input_data = []
        for input_config in input_modules:
            input_module = importlib.import_module(input_config["module"])
            input_client_cls = getattr(input_module, input_config["client_class"])

            init_params = input_config.get("init_params")
            if init_params:
                input_client = input_client_cls(**init_params)
            else:
                input_client = input_client_cls()

            input_method = getattr(input_client, input_config["method"])

            sig = inspect.signature(input_method)
            method_params = list(sig.parameters.keys())

            url = input_config.get("url")
            params = input_config.get("params", {})

            if url is not None and "params" in method_params:
                response = input_method(url, params=params)
            elif url is not None and len(method_params) > 0:
                response = input_method(url)
            else:
                response = input_method()

            input_data.append(response)

        # Instantiate post-processor with sample data
        module = importlib.import_module(module_name)
        processor_class = getattr(module, class_name)

        if method_name:
            processor_instance = processor_class()
            method = getattr(processor_instance, method_name)
            result = method(*input_data)
        else:
            result = processor_class(*input_data)

        # Analyze the result
        if isinstance(result, list) and len(result) > 0:
            sample = result[0]
        else:
            sample = result

        analysis = analyze_object(sample)

        if analysis.get("type") == "simple":
            vtype = analysis.get("value_type", "value")
            return (
                f"# Serializer not needed: Post-processor returns a simple "
                f"{vtype}, use auto-serialization"
            )

        fields = generate_serializer_config(analysis)

        toml_output = f"[serializers.{serializer_name}]\n"
        toml_output += f"[serializers.{serializer_name}.fields]\n"

        simple_fields = {k: v for k, v in fields.items() if isinstance(v, str)}
        for key, value in simple_fields.items():
            toml_output += f'{key} = "{value}"\n'

        complex_fields: dict[str, Any] = {
            k: v for k, v in fields.items() if isinstance(v, dict)
        }
        for key, value in complex_fields.items():
            if not isinstance(value, dict):
                continue
            toml_output += f"\n[serializers.{serializer_name}.fields.{key}]\n"
            toml_output += f'method = "{value["method"]}"\n'

            if "fields" in value:
                toml_output += f"[serializers.{serializer_name}.fields.{key}.fields]\n"
                for fk, fv in value["fields"].items():
                    if isinstance(fv, str):
                        toml_output += f'{fk} = "{fv}"\n'
                    elif isinstance(fv, dict) and "iterate" in fv:
                        iterate = fv["iterate"]
                        fields_str = ", ".join(
                            [
                                f'{k} = "{v}"'
                                for k, v in iterate.get("fields", {}).items()
                            ]
                        )
                        toml_output += (
                            f"[serializers.{serializer_name}.fields.{key}."
                            f"fields.variables]\n"
                        )
                        toml_output += (
                            f'iterate = {{ count = "{iterate["count"]}", '
                            f'item = "{iterate["item"]}", '
                            f"fields = {{ {fields_str} }} }}\n"
                        )

            if "iterate" in value:
                iterate = value["iterate"]
                fields_str = ", ".join(
                    [f'{k} = "{v}"' for k, v in iterate.get("fields", {}).items()]
                )
                toml_output += (
                    f"[serializers.{serializer_name}.fields.{key}.fields.variables]\n"
                )
                toml_output += (
                    f'iterate = {{ count = "{iterate["count"]}", '
                    f'item = "{iterate["item"]}", '
                    f"fields = {{ {fields_str} }} }}\n"
                )

        return toml_output

    except Exception as e:
        return f"# Error generating post-processor serializer: {e}"
