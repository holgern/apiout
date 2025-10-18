import importlib
import inspect
from typing import Any, Optional

from .serializer import serialize_response


def resolve_serializer(
    api_config: dict[str, Any], global_serializers: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    serializer_config: Any = api_config.get("serializer", {})

    if isinstance(serializer_config, str) and global_serializers:
        return global_serializers.get(serializer_config, {})

    if isinstance(serializer_config, dict):
        return serializer_config
    return {}


def fetch_api_data(
    api_config: dict[str, Any], global_serializers: Optional[dict[str, Any]] = None
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

        sig = inspect.signature(method)
        param_names = list(sig.parameters.keys())

        if "params" in param_names:
            responses = method(url, params=params)
        elif len(param_names) >= 1:
            responses = method(url)
        else:
            responses = method()

        serializer_config = resolve_serializer(api_config, global_serializers)
        return serialize_response(responses, serializer_config)

    except ImportError as e:
        return {"error": f"Failed to import module: {e}"}
    except AttributeError as e:
        return {"error": f"Failed to access class or method: {e}"}
    except Exception as e:
        return {"error": f"Failed to fetch data: {e}"}


def process_post_processor(
    post_processor_config: dict[str, Any],
    api_results: dict[str, Any],
    global_serializers: Optional[dict[str, Any]] = None,
) -> Any:
    try:
        module_name = post_processor_config.get("module")
        if not module_name:
            return {"error": "No module specified for post-processor"}

        class_name = post_processor_config.get("class")
        if not class_name:
            return {"error": "No class specified for post-processor"}

        inputs = post_processor_config.get("inputs", [])
        if not inputs:
            return {"error": "No inputs specified for post-processor"}

        for input_name in inputs:
            if input_name not in api_results:
                return {
                    "error": f"Required input '{input_name}' not found in API results"
                }

        module = importlib.import_module(module_name)
        processor_class = getattr(module, class_name)

        input_data = [api_results[input_name] for input_name in inputs]

        method_name = post_processor_config.get("method")
        if method_name:
            processor_instance = processor_class()
            method = getattr(processor_instance, method_name)
            result = method(*input_data)
        else:
            result = processor_class(*input_data)

        serializer_config = resolve_serializer(
            post_processor_config, global_serializers
        )
        return serialize_response(result, serializer_config)

    except ImportError as e:
        return {"error": f"Failed to import post-processor module: {e}"}
    except AttributeError as e:
        return {"error": f"Failed to access post-processor class or method: {e}"}
    except Exception as e:
        return {"error": f"Failed to process post-processor: {e}"}
