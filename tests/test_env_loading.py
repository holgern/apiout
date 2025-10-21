"""Tests for environment file loading functionality."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import typer

from apiout.cli import _get_config_dir, _load_config_files, _load_env_file


class TestGetConfigDir:
    """Tests for _get_config_dir function."""

    def test_default_config_dir(self):
        """Test default config directory returns a valid path."""
        # Don't clear environment on Windows - need HOME/USERPROFILE
        if os.name == "nt":
            # On Windows, ensure LOCALAPPDATA is available or test will use fallback
            config_dir = _get_config_dir()
            # Just verify it's a Path and contains "apiout"
            assert isinstance(config_dir, Path)
            assert config_dir.name == "apiout"
        else:
            # On Unix, can safely clear environment
            with patch.dict(os.environ, {}, clear=True):
                config_dir = _get_config_dir()
                assert config_dir == Path.home() / ".config" / "apiout"

    def test_xdg_config_home_override(self):
        """Test XDG_CONFIG_HOME environment variable override."""
        custom_config = "/custom/config"
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": custom_config}):
            config_dir = _get_config_dir()
            assert config_dir == Path(custom_config) / "apiout"

    def test_xdg_config_home_with_tilde(self):
        """Test XDG_CONFIG_HOME with tilde expansion."""
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": "~/custom_config"}):
            config_dir = _get_config_dir()
            expected = Path.home() / "custom_config" / "apiout"
            assert config_dir == expected

    def test_windows_localappdata(self):
        """Test Windows LOCALAPPDATA usage when available."""
        if os.name == "nt":
            # Test only on actual Windows
            local_app_data = os.environ.get("LOCALAPPDATA")
            if local_app_data:
                # Clear XDG_CONFIG_HOME to ensure LOCALAPPDATA is used
                env = {k: v for k, v in os.environ.items() if k != "XDG_CONFIG_HOME"}
                with patch.dict(os.environ, env, clear=True):
                    config_dir = _get_config_dir()
                    assert config_dir == Path(local_app_data) / "apiout"
        else:
            pytest.skip("Windows-specific test")


class TestLoadEnvFile:
    """Tests for _load_env_file function."""

    def test_load_existing_env_file(self):
        """Test loading an existing environment file returns path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_dir = Path(tmpdir)
            env_file = env_dir / "test_env.toml"
            env_file.write_text("""
[clients.test]
module = "test_module"

[[apis]]
name = "test_api"
""")

            with patch("apiout.cli._get_config_dir", return_value=env_dir):
                result = _load_env_file("test_env")
                assert result == env_file
                assert result.exists()

    def test_load_missing_env_file(self):
        """Test loading a non-existent environment file raises typer.Exit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_dir = Path(tmpdir)

            with patch("apiout.cli._get_config_dir", return_value=env_dir):
                with pytest.raises(typer.Exit):
                    _load_env_file("nonexistent")


class TestLoadConfigFilesWithEnv:
    """Tests for _load_config_files with environment files."""

    def test_load_single_config(self):
        """Test loading a single config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.toml"
            config_file.write_text("""
[clients.client1]
module = "module1"

[[apis]]
name = "api1"
url = "http://example.com"
""")

            result = _load_config_files([config_file])

            assert "clients" in result
            assert "client1" in result["clients"]
            assert result["apis"][0]["name"] == "api1"

    def test_load_multiple_configs(self):
        """Test loading multiple config files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            config1 = tmpdir / "config1.toml"
            config1.write_text("""
[clients.client1]
module = "module1"

[[apis]]
name = "api1"
url = "http://example1.com"
""")

            config2 = tmpdir / "config2.toml"
            config2.write_text("""
[clients.client2]
module = "module2"

[[apis]]
name = "api2"
url = "http://example2.com"
""")

            result = _load_config_files([config1, config2])

            assert "client1" in result["clients"]
            assert "client2" in result["clients"]
            assert len(result["apis"]) == 2
            assert result["apis"][0]["name"] == "api1"
            assert result["apis"][1]["name"] == "api2"

    def test_config_with_scoped_serializers(self):
        """Test config files with client-scoped serializers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.toml"
            config_file.write_text("""
[clients.test_client]
module = "test"

[serializers.test_client.ser1]
[serializers.test_client.ser1.fields]
field1 = "mapped1"

[[apis]]
name = "test_api"
client = "test_client"
url = "http://test.com"
serializer = "ser1"
""")

            result = _load_config_files([config_file])

            assert "test_client.ser1" in result["serializers"]
            assert (
                result["serializers"]["test_client.ser1"]["fields"]["field1"]
                == "mapped1"
            )

    def test_config_with_global_serializers(self):
        """Test config files with global (non-scoped) serializers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.toml"
            config_file.write_text("""
[clients.test_client]
module = "test"

[serializers.global_ser]
[serializers.global_ser.fields]
field1 = "mapped1"

[[apis]]
name = "test_api"
client = "test_client"
url = "http://test.com"
serializer = "global_ser"
""")

            result = _load_config_files([config_file])

            assert "global_ser" in result["serializers"]
            assert result["serializers"]["global_ser"]["fields"]["field1"] == "mapped1"

    def test_missing_config_file(self):
        """Test loading non-existent config file raises typer.Exit."""
        with pytest.raises(typer.Exit):
            _load_config_files([Path("/nonexistent/config.toml")])
