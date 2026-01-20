"""Explanation Service - Stub for sentence analysis/explanation via Gemini."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExplanationResult:
    """Result of an explanation request."""

    text: Optional[str]
    model: Optional[str]
    error: Optional[str] = None

    def is_success(self) -> bool:
        """Return True when the call produced a usable explanation."""
        return self.error is None and self.text is not None


class ExplanationService(ABC):
    """
    Abstract service for providing sentence analysis/explanation.

    Implementations (e.g., GeminiExplanationService) handle API calls.
    """

    @abstractmethod
    def explain(self, original_jp: str, translation_en: str, api_key: str) -> ExplanationResult:
        """Provide explanation/analysis for Japanese text.

        Args:
            original_jp: Original Japanese text from OCR block.
            translation_en: English translation to ground the explanation.
            api_key: Gemini API key for authentication.

        Returns:
            ExplanationResult with explanation text or error message.
        """
        pass
