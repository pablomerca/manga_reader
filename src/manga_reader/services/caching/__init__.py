"""Caching services - abstract interface and concrete implementations."""

from manga_reader.services.caching.translation_cache import TranslationCache, CacheRecord
from manga_reader.services.caching.in_memory_translation_cache import InMemoryTranslationCache
from manga_reader.services.caching.file_translation_cache import FileTranslationCache

__all__ = [
    "TranslationCache",
    "CacheRecord",
    "InMemoryTranslationCache",
    "FileTranslationCache",
]
