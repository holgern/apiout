import importlib
from typing import Any, Dict, Optional

from .serializer import serialize_response


def resolve_serializer(
    api_config: Dict[str, Any], global_serializers: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    serializer_config = api_config.get("serializer", {})

    if isinstance(serializer_config, str) and global_serializers:
        return global_serializers.get(serializer_config, {})

    return serializer_config


def fetch_api_data(
    api_config: Dict[str, Any], global_serializers: Optional[Dict[str, Any]] = None
) -> Any:
    try:
        module_name = api_config.get("module")
        if not module_name:
            return {"error": "No module specified"}

        method_name = api_config.get("method")
        if not method_name:
            return {"error": "No method specified"}

        module = importlib.import_module(module_name)

        client_class_name = api_config.get("client_class", "Client")
        client_class = getattr(module, client_class_name)
        client = client_class()

        method = getattr(client, method_name)

        url = api_config.get("url", "")
        params = api_config.get("params", {})

        responses = method(url, params=params)

        serializer_config = resolve_serializer(api_config, global_serializers)
        return serialize_response(responses, serializer_config)

    except ImportError as e:
        return {"error": f"Failed to import module: {e}"}
    except AttributeError as e:
        return {"error": f"Failed to access class or method: {e}"}
    except Exception as e:
        return {"error": f"Failed to fetch data: {e}"}
