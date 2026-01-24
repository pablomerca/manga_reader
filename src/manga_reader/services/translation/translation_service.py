"""Translation Service - Stub for JA→EN translation via Gemini."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class TranslationResult:
    """Result of a translation request."""

    text: str
    model: str
    error: Optional[str] = None

    @property
    def is_error(self) -> bool:
        """True if translation failed."""
        return self.error is not None


class TranslationService(ABC):
    """
    Abstract service for translating Japanese text to English.

    Implementations (e.g., GeminiTranslationService) handle API calls.
    """

    @abstractmethod
    def translate(self, text: str, api_key: str) -> TranslationResult:
        """
        Translate Japanese text to English.

        Args:
            text: Japanese text to translate.
            api_key: Modelo provider API key for authentication.

        Returns:
            TranslationResult with text or error message.
        """
        pass
