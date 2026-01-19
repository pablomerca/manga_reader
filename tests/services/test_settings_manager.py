"""Unit tests for SettingsManager."""

import os
import tempfile
from pathlib import Path

import pytest

from manga_reader.services import SettingsManager


@pytest.fixture
def temp_env_dir():
    """Provide a temporary directory for .env files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def clean_env():
    """Clean up GEMINI_API_KEY from environment before and after test."""
    old_value = os.environ.pop("GEMINI_API_KEY", None)
    yield
    if old_value is not None:
        os.environ["GEMINI_API_KEY"] = old_value
    else:
        os.environ.pop("GEMINI_API_KEY", None)


@pytest.fixture
def settings(temp_env_dir, clean_env):
    """Provide a SettingsManager with a test .env file."""
    env_file = temp_env_dir / ".env"
    env_file.write_text("GEMINI_API_KEY=\n")
    return SettingsManager(project_root=temp_env_dir)


class TestSettingsManagerAPIKey:
    """Tests for API key management from .env file."""

    def test_get_api_key_returns_none_when_empty(self, settings):
        """API key should be None when .env has empty value."""
        assert settings.get_gemini_api_key() is None

    def test_get_api_key_returns_value_from_env(self, temp_env_dir, clean_env):
        """API key should be read from .env file."""
        env_file = temp_env_dir / ".env"
        env_file.write_text("GEMINI_API_KEY=test-key-123\n")
        os.environ["GEMINI_API_KEY"] = "test-key-123"
        
        settings = SettingsManager(project_root=temp_env_dir)
        assert settings.get_gemini_api_key() == "test-key-123"

    def test_get_api_key_strips_whitespace(self, temp_env_dir, clean_env):
        """API key should strip leading/trailing whitespace."""
        env_file = temp_env_dir / ".env"
        env_file.write_text("GEMINI_API_KEY=  test-key  \n")
        os.environ["GEMINI_API_KEY"] = "  test-key  "
        
        settings = SettingsManager(project_root=temp_env_dir)
        assert settings.get_gemini_api_key() == "test-key"

    def test_get_api_key_returns_none_for_whitespace_only(self, temp_env_dir, clean_env):
        """API key should return None for whitespace-only value."""
        env_file = temp_env_dir / ".env"
        env_file.write_text("GEMINI_API_KEY=   \n")
        os.environ["GEMINI_API_KEY"] = "   "
        
        settings = SettingsManager(project_root=temp_env_dir)
        assert settings.get_gemini_api_key() is None

    def test_reload_env_updates_api_key(self, temp_env_dir, clean_env):
        """reload_env should pick up changes to .env file."""
        env_file = temp_env_dir / ".env"
        env_file.write_text("GEMINI_API_KEY=old-key\n")
        os.environ["GEMINI_API_KEY"] = "old-key"
        
        settings = SettingsManager(project_root=temp_env_dir)
        assert settings.get_gemini_api_key() == "old-key"
        
        env_file.write_text("GEMINI_API_KEY=new-key\n")
        os.environ["GEMINI_API_KEY"] = "new-key"
        settings.reload_env()
        assert settings.get_gemini_api_key() == "new-key"

    def test_missing_env_file_returns_none(self, temp_env_dir, clean_env):
        """SettingsManager should handle missing .env file gracefully."""
        env_file = temp_env_dir / ".env"
        if env_file.exists():
            env_file.unlink()
        
        settings = SettingsManager(project_root=temp_env_dir)
        assert settings.get_gemini_api_key() is None
