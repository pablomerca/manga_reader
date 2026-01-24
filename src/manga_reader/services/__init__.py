"""Services layer - business logic and external integrations."""

from manga_reader.services.dictionary_service import DictionaryEntry, DictionarySense, DictionaryService
from manga_reader.services.morphology_service import MorphologyService, Token
from manga_reader.services.vocabulary_service import VocabularyService
from manga_reader.services.thumbnail_service import ThumbnailService
from manga_reader.services.translation_cache import TranslationCache, CacheRecord
from manga_reader.services.in_memory_translation_cache import InMemoryTranslationCache
from manga_reader.services.file_translation_cache import FileTranslationCache
from manga_reader.services.translation_service import TranslationService, TranslationResult
from manga_reader.services.gemini_translation_service import GeminiTranslationService
from manga_reader.services.gemini_explanation_service import GeminiExplanationService
from manga_reader.services.explanation_service import ExplanationService, ExplanationResult
from manga_reader.services.settings_manager import SettingsManager
from manga_reader.services.text_normalization import normalize_text
from manga_reader.services.api_workers import TranslationWorker, ExplanationWorker, WorkerSignals

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
	"FileTranslationCache",
	"TranslationService",
	"TranslationResult",
	"GeminiTranslationService",
	"GeminiExplanationService",
	"ExplanationService",
	"ExplanationResult",
	"SettingsManager",
	"normalize_text",
	"TranslationWorker",
	"ExplanationWorker",
	"WorkerSignals",
]
