"""Services layer - business logic and external integrations."""

from manga_reader.services.dictionary_service import (
	BreadcrumbItem,
	DictionaryEntry,
	DictionaryEntryFull,
	DictionaryLookupResult,
	DictionarySense,
	DictionaryService,
	KanjiEntry,
)
from manga_reader.services.vocabulary_service import VocabularyService
from manga_reader.services.thumbnail_service import ThumbnailService
from manga_reader.services.settings_manager import SettingsManager

# Text processing services
from manga_reader.services.text_processing import MorphologyService, Token, normalize_text, TranslationWorker, ExplanationWorker, WorkerSignals

# Translation services
from manga_reader.services.translation import TranslationService, TranslationResult, GeminiTranslationService

# Explanation services
from manga_reader.services.explanation import ExplanationService, ExplanationResult, GeminiExplanationService

# Caching services
from manga_reader.services.caching import TranslationCache, CacheRecord, InMemoryTranslationCache, FileTranslationCache

__all__ = [
	"DictionaryEntry",
	"DictionaryEntryFull",
	"DictionaryLookupResult",
	"DictionarySense",
	"KanjiEntry",
	"BreadcrumbItem",
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
