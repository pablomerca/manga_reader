"""Explanation services - abstract interface and Gemini implementation."""

from manga_reader.services.explanation.explanation_service import ExplanationService, ExplanationResult
from manga_reader.services.explanation.gemini_explanation_service import GeminiExplanationService

__all__ = [
    "ExplanationService",
    "ExplanationResult",
    "GeminiExplanationService",
]
