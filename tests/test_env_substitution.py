"""Tests for environment variable substitution in configuration."""

import os
from unittest.mock import patch

from apiout.fetcher import _substitute_env_vars, _substitute_vars


class TestEnvVarSubstitution:
    """Tests for _substitute_env_vars function."""

    def test_substitute_simple_string(self):
        """Test substitution in a simple string."""
        with patch.dict(os.environ, {"API_KEY": "secret123"}):
            result = _substitute_env_vars("Bearer ${API_KEY}")
            assert result == "Bearer secret123"

    def test_substitute_multiple_vars(self):
        """Test substitution of multiple variables in one string."""
        with patch.dict(os.environ, {"HOST": "example.com", "PORT": "8080"}):
            result = _substitute_env_vars("https://${HOST}:${PORT}/api")
            assert result == "https://example.com:8080/api"

    def test_substitute_missing_var(self):
        """Test that missing variables are left unchanged."""
        with patch.dict(os.environ, {}, clear=True):
            result = _substitute_env_vars("Bearer ${MISSING_KEY}")
            assert result == "Bearer ${MISSING_KEY}"

    def test_substitute_in_dict(self):
        """Test substitution in dictionary values."""
        with patch.dict(os.environ, {"API_KEY": "secret123", "USER": "admin"}):
            result = _substitute_env_vars(
                {
                    "Authorization": "Bearer ${API_KEY}",
                    "X-User": "${USER}",
                    "X-Static": "static_value",
                }
            )
            assert result == {
                "Authorization": "Bearer secret123",
                "X-User": "admin",
                "X-Static": "static_value",
            }

    def test_substitute_in_list(self):
        """Test substitution in list items."""
        with patch.dict(os.environ, {"VAR1": "value1", "VAR2": "value2"}):
            result = _substitute_env_vars(["${VAR1}", "${VAR2}", "static"])
            assert result == ["value1", "value2", "static"]

    def test_substitute_in_nested_dict(self):
        """Test substitution in nested dictionaries."""
        with patch.dict(os.environ, {"KEY": "secret"}):
            result = _substitute_env_vars(
                {"outer": {"inner": "${KEY}", "list": ["${KEY}", "static"]}}
            )
            assert result == {
                "outer": {"inner": "secret", "list": ["secret", "static"]}
            }

    def test_substitute_non_string_types(self):
        """Test that non-string types are returned unchanged."""
        result = _substitute_env_vars(123)
        assert result == 123

        result = _substitute_env_vars(None)
        assert result is None

        result = _substitute_env_vars(True)
        assert result is True

    def test_substitute_preserves_dict_with_non_string_values(self):
        """Test that dicts with non-string values preserve those values."""
        with patch.dict(os.environ, {"KEY": "value"}):
            result = _substitute_env_vars(
                {"string": "${KEY}", "number": 42, "boolean": True, "none": None}
            )
            assert result == {
                "string": "value",
                "number": 42,
                "boolean": True,
                "none": None,
            }

    def test_substitute_partial_match(self):
        """Test that only complete ${VAR} patterns are substituted."""
        with patch.dict(os.environ, {"VAR": "replaced"}):
            result = _substitute_env_vars("$VAR ${VAR} ${VAR")
            assert result == "$VAR replaced ${VAR"

    def test_substitute_empty_var_name(self):
        """Test handling of empty variable name ${}."""
        result = _substitute_env_vars("test ${} value")
        assert result == "test ${} value"


class TestVarSubstitution:
    """Tests for _substitute_vars function with priority order."""

    def test_substitute_vars_runtime_priority(self):
        """Test that runtime params have highest priority."""
        result = _substitute_vars(
            "Bearer ${TOKEN}",
            method_params={"TOKEN": "method_default"},
            user_params={"TOKEN": "runtime_value"},
            param_defaults={"TOKEN": "param_default"},
        )
        assert result == "Bearer runtime_value"

    def test_substitute_vars_method_params_priority(self):
        """Test that method_params have second priority."""
        result = _substitute_vars(
            "Bearer ${TOKEN}",
            method_params={"TOKEN": "method_value"},
            user_params=None,
            param_defaults={"TOKEN": "param_default"},
        )
        assert result == "Bearer method_value"

    def test_substitute_vars_param_defaults_priority(self):
        """Test that param_defaults have third priority."""
        result = _substitute_vars(
            "Bearer ${TOKEN}",
            method_params=None,
            user_params=None,
            param_defaults={"TOKEN": "param_default"},
        )
        assert result == "Bearer param_default"

    def test_substitute_vars_env_fallback(self):
        """Test environment variables as fallback."""
        with patch.dict(os.environ, {"TOKEN": "env_value"}):
            result = _substitute_vars(
                "Bearer ${TOKEN}",
                method_params=None,
                user_params=None,
                param_defaults=None,
            )
            assert result == "Bearer env_value"

    def test_substitute_vars_missing_var(self):
        """Test missing variable remains unchanged."""
        result = _substitute_vars(
            "Bearer ${MISSING}",
            method_params=None,
            user_params=None,
            param_defaults=None,
        )
        assert result == "Bearer ${MISSING}"

    def test_substitute_vars_in_dict(self):
        """Test substitution in dictionary values."""
        result = _substitute_vars(
            {"url": "https://${HOST}/api", "key": "${API_KEY}"},
            method_params={"HOST": "example.com"},
            user_params=None,
            param_defaults={"API_KEY": "default_key"},
        )
        expected = {"url": "https://example.com/api", "key": "default_key"}
        assert result == expected

    def test_substitute_vars_in_nested_dict(self):
        """Test substitution in nested dictionaries."""
        result = _substitute_vars(
            {"auth": {"token": "${TOKEN}"}, "endpoint": "${HOST}"},
            method_params={"TOKEN": "secret"},
            user_params=None,
            param_defaults={"HOST": "localhost"},
        )
        expected = {"auth": {"token": "secret"}, "endpoint": "localhost"}
        assert result == expected
