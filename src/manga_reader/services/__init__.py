"""Services layer - business logic and external integrations."""

from manga_reader.services.dictionary_service import DictionaryEntry, DictionarySense, DictionaryService
from manga_reader.services.morphology_service import MorphologyService, Token
from manga_reader.services.vocabulary_service import VocabularyService
from manga_reader.services.thumbnail_service import ThumbnailService
from manga_reader.services.translation_cache import TranslationCache, CacheRecord
from manga_reader.services.in_memory_translation_cache import InMemoryTranslationCache
from manga_reader.services.translation_service import TranslationService, TranslationResult
from manga_reader.services.explanation_service import ExplanationService, ExplanationResult
from manga_reader.services.settings_manager import SettingsManager

__all__ = [
	"DictionaryEntry",
	"DictionarySense",
	"DictionaryService",
	"MorphologyService",
	"Token",
	"VocabularyService",
	"ThumbnailService",
	"TranslationCache",
	"CacheRecord",
	"InMemoryTranslationCache",
	"TranslationService",
	"TranslationResult",
	"ExplanationService",
	"ExplanationResult",
	"SettingsManager",
]
