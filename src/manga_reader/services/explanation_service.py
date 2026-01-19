"""Explanation Service - Stub for sentence analysis/explanation via Gemini."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExplanationResult:
    """Result of an explanation request."""

    text: str
    model: str
    error: Optional[str] = None

    @property
    def is_error(self) -> bool:
        """True if explanation request failed."""
        return self.error is not None


class ExplanationService(ABC):
    """
    Abstract service for providing sentence analysis/explanation.

    Implementations (e.g., GeminiExplanationService) handle API calls.
    """

    @abstractmethod
    def explain(self, text: str, api_key: str) -> ExplanationResult:
        """
        Provide explanation/analysis for Japanese text.

        Args:
            text: Japanese text to explain.
            api_key: Gemini API key for authentication.

        Returns:
            ExplanationResult with explanation text or error message.
        """
        pass
