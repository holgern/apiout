"""Tests for environment variable substitution in configuration."""

import os
from unittest.mock import patch

from apiout.fetcher import _substitute_env_vars


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
