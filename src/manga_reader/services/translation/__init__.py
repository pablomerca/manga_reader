"""Translation services - abstract interface and Gemini implementation."""

from manga_reader.services.translation.translation_service import TranslationService, TranslationResult
from manga_reader.services.translation.gemini_translation_service import GeminiTranslationService

__all__ = [
    "TranslationService",
    "TranslationResult",
    "GeminiTranslationService",
]
