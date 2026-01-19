"""Settings Manager - Placeholder for API key and feature configuration."""

from typing import Optional


class SettingsManager:
    """
    Placeholder for settings persistence.

    For MVP, holds values in memory. Can be extended to persist to QSettings or config file.
    """

    def __init__(self):
        self._gemini_api_key: Optional[str] = None

    def get_gemini_api_key(self) -> Optional[str]:
        """Get the Gemini API key if set."""
        return self._gemini_api_key

    def set_gemini_api_key(self, key: str) -> None:
        """Set the Gemini API key."""
        self._gemini_api_key = key if key.strip() else None

    def clear_api_key(self) -> None:
        """Clear the stored API key."""
        self._gemini_api_key = None
