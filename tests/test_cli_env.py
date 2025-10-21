"""Integration tests for CLI with environment flags."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from apiout.cli import app

runner = CliRunner()


def test_cli_with_env_flag():
    """Test CLI with -e/--env flag loads environment file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_dir = Path(tmpdir)

        # Create a test environment file
        env_file = env_dir / "test.toml"
        env_file.write_text("""
[clients.mock_client]
module = "unittest.mock"
client_class = "Mock"

[[apis]]
name = "test_api"
module = "unittest.mock"
method = "Mock"
url = "http://example.com"
""")

        # Mock the config directory
        with patch("apiout.cli._get_config_dir", return_value=env_dir):
            result = runner.invoke(app, ["run", "-e", "test", "--json"])

        # Should succeed (won't actually call API with mock)
        assert result.exit_code == 0


def test_cli_with_multiple_env_flags():
    """Test CLI with multiple -e flags."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_dir = Path(tmpdir)

        # Create two environment files
        env1 = env_dir / "env1.toml"
        env1.write_text("""
[clients.client1]
module = "unittest.mock"
client_class = "Mock"

[[apis]]
name = "api1"
module = "unittest.mock"
method = "Mock"
url = "http://example1.com"
""")

        env2 = env_dir / "env2.toml"
        env2.write_text("""
[clients.client2]
module = "unittest.mock"
client_class = "Mock"

[[apis]]
name = "api2"
module = "unittest.mock"
method = "Mock"
url = "http://example2.com"
""")

        with patch("apiout.cli._get_config_dir", return_value=env_dir):
            result = runner.invoke(app, ["run", "-e", "env1", "-e", "env2", "--json"])

        assert result.exit_code == 0


def test_cli_with_env_and_config():
    """Test CLI with both -e and -c flags."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        env_dir = tmpdir / "envs"
        env_dir.mkdir()
        config_dir = tmpdir / "configs"
        config_dir.mkdir()

        # Create environment file
        env_file = env_dir / "env1.toml"
        env_file.write_text("""
[clients.env_client]
module = "unittest.mock"
client_class = "Mock"

[[apis]]
name = "env_api"
module = "unittest.mock"
method = "Mock"
url = "http://env.com"
""")

        # Create config file
        config_file = config_dir / "config.toml"
        config_file.write_text("""
[clients.config_client]
module = "unittest.mock"
client_class = "Mock"

[[apis]]
name = "config_api"
module = "unittest.mock"
method = "Mock"
url = "http://config.com"
""")

        with patch("apiout.cli._get_config_dir", return_value=env_dir):
            result = runner.invoke(
                app, ["run", "-e", "env1", "-c", str(config_file), "--json"]
            )

        assert result.exit_code == 0


def test_cli_missing_env_file():
    """Test CLI with non-existent environment file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_dir = Path(tmpdir)

        with patch("apiout.cli._get_config_dir", return_value=env_dir):
            result = runner.invoke(app, ["run", "-e", "nonexistent", "--json"])

        assert result.exit_code == 1


def test_cli_no_config_or_env():
    """Test CLI without any config or env flags."""
    result = runner.invoke(app, ["run", "--json"])

    assert result.exit_code == 1
