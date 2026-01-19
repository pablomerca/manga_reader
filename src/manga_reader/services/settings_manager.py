"""Settings Manager - Handles API key and feature configuration."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


class SettingsManager:
    """
    Manages settings and API key configuration.

    For MVP, reads API key from .env file in project root.
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize settings manager.

        Args:
            project_root: Path to project root where .env is located.
                         If None, searches upward from current file.
        """
        if project_root is None:
            current = Path(__file__).resolve()
            project_root = current.parent.parent.parent.parent
        
        env_path = project_root / ".env"
        load_dotenv(dotenv_path=env_path)
        
        self._project_root = project_root

    def get_gemini_api_key(self) -> Optional[str]:
        """Get the Gemini API key from environment."""
        key = os.getenv("GEMINI_API_KEY")
        return key.strip() if key and key.strip() else None

    def reload_env(self) -> None:
        """Reload environment variables from .env file."""
        env_path = self._project_root / ".env"
        load_dotenv(dotenv_path=env_path, override=True)
