import importlib
import inspect
from typing import Any, Dict, List, Set


def is_simple_type(obj: Any) -> bool:
    return isinstance(obj, (str, int, float, bool, type(None)))


def is_collection(obj: Any) -> bool:
    return isinstance(obj, (list, tuple))


def get_methods_and_attrs(obj: Any) -> tuple[List[str], List[str]]:
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
    obj: Any, max_depth: int = 3, current_depth: int = 0, visited: Set[int] = None
) -> Dict[str, Any]:
    if visited is None:
        visited = set()

    obj_id = id(obj)
    if obj_id in visited or current_depth >= max_depth:
        return {}

    visited.add(obj_id)

    if is_simple_type(obj):
        return {"type": "simple", "value_type": type(obj).__name__}

    if is_collection(obj):
        if len(obj) > 0:
            item_analysis = analyze_object(
                obj[0], max_depth, current_depth + 1, visited
            )
            return {"type": "collection", "item": item_analysis}
        return {"type": "collection", "item": {}}

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
                result["methods"][method_name] = analyze_object(
                    method_result, max_depth, current_depth + 1, visited
                )
            elif len(params) == 1 or (len(params) == 2 and params[0] == "self"):
                result["methods"][method_name] = {
                    "type": "indexed_method",
                    "note": "Takes index parameter, likely for iteration",
                }
        except Exception as e:
            result["methods"][method_name] = {"type": "error", "error": str(e)}

    for attr_name in attrs:
        try:
            attr = getattr(obj, attr_name)
            result["attributes"][attr_name] = analyze_object(
                attr, max_depth, current_depth + 1, visited
            )
        except Exception:
            pass

    return result


def generate_serializer_config(
    analysis: Dict[str, Any], prefix: str = ""
) -> Dict[str, Any]:
    if analysis.get("type") == "simple":
        return {}

    if analysis.get("type") == "collection":
        return {}

    if analysis.get("type") != "object":
        return {}

    fields = {}

    for method_name, method_info in analysis.get("methods", {}).items():
        if method_info.get("type") == "simple":
            fields[method_name.lower()] = method_name

        elif method_info.get("type") == "indexed_method":
            continue

        elif method_info.get("type") == "object":
            nested_class = method_info.get("class", "")

            if "Length" in method_name or "Count" in method_name:
                continue

            item_method_name = (
                method_name.replace("Current", "")
                .replace("Hourly", "")
                .replace("Daily", "")
            )
            possible_count = f"{item_method_name}Length"
            possible_item = (
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
                            item_fields[m_name.lower()] = m_name

                    fields[method_name.lower()] = {
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
                        fields[method_name.lower()] = {
                            "method": method_name,
                            "fields": nested_config,
                        }
            else:
                nested_config = generate_serializer_config(
                    method_info, f"{prefix}{method_name}."
                )
                if nested_config:
                    fields[method_name.lower()] = {
                        "method": method_name,
                        "fields": nested_config,
                    }

    for attr_name, attr_info in analysis.get("attributes", {}).items():
        if attr_info.get("type") == "simple":
            fields[attr_name.lower()] = attr_name

    return fields


def generate_toml_serializer(name: str, fields: Dict[str, Any], indent: int = 0) -> str:
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
                        f'iterate = {{ count = "{iterate["count"]}", item = "{iterate["item"]}", fields = {{ {fields_str} }} }}'
                    )

    return "\n".join(lines)


def introspect_and_generate(
    module_name: str,
    client_class: str,
    method_name: str,
    url: str,
    params: Dict[str, Any],
    serializer_name: str = "generated",
) -> str:
    try:
        module = importlib.import_module(module_name)
        client_cls = getattr(module, client_class)
        client = client_cls()
        method = getattr(client, method_name)

        response = method(url, params=params)

        if isinstance(response, list) and len(response) > 0:
            sample = response[0]
        else:
            sample = response

        analysis = analyze_object(sample)

        fields = generate_serializer_config(analysis)

        toml_output = f"[serializers.{serializer_name}]\n"
        toml_output += f"[serializers.{serializer_name}.fields]\n"

        simple_fields = {k: v for k, v in fields.items() if isinstance(v, str)}
        for key, value in simple_fields.items():
            toml_output += f'{key} = "{value}"\n'

        complex_fields = {k: v for k, v in fields.items() if isinstance(v, dict)}
        for key, value in complex_fields.items():
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
                        toml_output += f"[serializers.{serializer_name}.fields.{key}.fields.variables]\n"
                        toml_output += f'iterate = {{ count = "{iterate["count"]}", item = "{iterate["item"]}", fields = {{ {fields_str} }} }}\n'

            if "iterate" in value:
                iterate = value["iterate"]
                fields_str = ", ".join(
                    [f'{k} = "{v}"' for k, v in iterate.get("fields", {}).items()]
                )
                toml_output += (
                    f"[serializers.{serializer_name}.fields.{key}.fields.variables]\n"
                )
                toml_output += f'iterate = {{ count = "{iterate["count"]}", item = "{iterate["item"]}", fields = {{ {fields_str} }} }}\n'

        return toml_output

    except Exception as e:
        return f"# Error generating serializer: {e}"
