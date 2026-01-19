"""Unit tests for SettingsManager."""

import pytest

from manga_reader.services import SettingsManager


@pytest.fixture
def settings():
    """Provide a fresh SettingsManager instance."""
    return SettingsManager()


class TestSettingsManagerAPIKey:
    """Tests for API key management."""

    def test_get_api_key_returns_none_initially(self, settings):
        """API key should be None on initialization."""
        assert settings.get_gemini_api_key() is None

    def test_set_api_key_stores_value(self, settings):
        """set_api_key should store the provided key."""
        settings.set_gemini_api_key("test-key-123")
        assert settings.get_gemini_api_key() == "test-key-123"

    def test_set_api_key_overwrites_previous(self, settings):
        """set_api_key should replace the previous key."""
        settings.set_gemini_api_key("old-key")
        settings.set_gemini_api_key("new-key")
        assert settings.get_gemini_api_key() == "new-key"

    def test_set_api_key_with_whitespace_only_sets_none(self, settings):
        """set_api_key with whitespace-only string should set None."""
        settings.set_gemini_api_key("   ")
        assert settings.get_gemini_api_key() is None

    def test_clear_api_key_removes_value(self, settings):
        """clear_api_key should reset the API key to None."""
        settings.set_gemini_api_key("test-key")
        settings.clear_api_key()
        assert settings.get_gemini_api_key() is None

    def test_clear_api_key_idempotent(self, settings):
        """clear_api_key should be safe to call multiple times."""
        settings.clear_api_key()
        settings.clear_api_key()
        assert settings.get_gemini_api_key() is None


class TestSettingsManagerAutoExplain:
    """Auto-explain feature removed; keeping class to signal removal in suite."""

    def test_auto_explain_feature_removed(self, settings):
        """Auto-explain should no longer exist or be enabled."""
        assert not hasattr(settings, "is_auto_explain_enabled")
        assert not hasattr(settings, "set_auto_explain_enabled")


class TestSettingsManagerIndependence:
    """Tests for independence of settings."""

    def test_api_key_setting_stands_alone(self, settings):
        """API key behavior is independent; no auto-explain toggles remain."""
        settings.set_gemini_api_key("test-key")
        assert settings.get_gemini_api_key() == "test-key"
