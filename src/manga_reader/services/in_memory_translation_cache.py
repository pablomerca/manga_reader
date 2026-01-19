"""In-memory translation cache for testing and session-level caching."""

from datetime import datetime
from typing import Optional

from manga_reader.services.translation_cache import CacheRecord, TranslationCache


class InMemoryTranslationCache(TranslationCache):
    """
    Simple in-memory cache implementation.

    Used for testing and session-level caching. No persistence.
    """

    def __init__(self):
        # Structure: {volume_id: {(normalized_text, lang): CacheRecord}}
        self._store: dict[str, dict[tuple[str, str], CacheRecord]] = {}

    def get(
        self, volume_id: str, normalized_text: str, lang: str = "en"
    ) -> Optional[CacheRecord]:
        """Retrieve a cached entry if it exists."""
        volume_cache = self._store.get(volume_id, {})
        key = (normalized_text, lang)
        return volume_cache.get(key)

    def put(
        self,
        volume_id: str,
        normalized_text: str,
        lang: str,
        record: CacheRecord,
    ) -> None:
        """Store or overwrite a cache entry."""
        if volume_id not in self._store:
            self._store[volume_id] = {}
        key = (normalized_text, lang)
        self._store[volume_id][key] = record

    def delete(
        self, volume_id: str, normalized_text: str, lang: str = "en"
    ) -> None:
        """Delete a single cache entry."""
        if volume_id in self._store:
            key = (normalized_text, lang)
            self._store[volume_id].pop(key, None)

    def clear_volume(self, volume_id: str) -> None:
        """Clear all cache entries for a volume."""
        self._store.pop(volume_id, None)

    def list_keys(self, volume_id: str) -> list[tuple[str, str]]:
        """List all (normalized_text, lang) keys for a volume."""
        volume_cache = self._store.get(volume_id, {})
        return list(volume_cache.keys())
