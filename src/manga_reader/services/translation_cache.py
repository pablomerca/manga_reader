"""Translation Cache abstraction - plugin interface for translation/explanation storage."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CacheRecord:
    """A cached translation/explanation entry."""

    normalized_text: str
    lang: str
    translation: Optional[str]
    explanation: Optional[str]
    model: str
    updated_at: datetime


class TranslationCache(ABC):
    """
    Abstract interface for caching translations and explanations.

    Implementations (FileTranslationCache, DbTranslationCache) handle storage details.
    This allows coordinators and services to depend on an abstraction, not concrete storage.
    """

    @abstractmethod
    def get(
        self, volume_id: str, normalized_text: str, lang: str = "en"
    ) -> Optional[CacheRecord]:
        """
        Retrieve a cached entry by volume_id, normalized text, and language.

        Args:
            volume_id: Identifier for the volume (e.g., volume path or UUID).
            normalized_text: Text query (trim/collapse whitespace applied beforehand).
            lang: Target language (default: "en").

        Returns:
            CacheRecord if found, else None.
        """
        pass

    @abstractmethod
    def put(
        self,
        volume_id: str,
        normalized_text: str,
        lang: str,
        record: CacheRecord,
    ) -> None:
        """
        Store or overwrite a cache entry.

        Args:
            volume_id: Identifier for the volume.
            normalized_text: Text query key.
            lang: Target language.
            record: CacheRecord with translation/explanation and metadata.
        """
        pass

    @abstractmethod
    def delete(
        self, volume_id: str, normalized_text: str, lang: str = "en"
    ) -> None:
        """Delete a single cache entry."""
        pass

    @abstractmethod
    def clear_volume(self, volume_id: str) -> None:
        """Clear all cache entries for a given volume."""
        pass

    @abstractmethod
    def list_keys(self, volume_id: str) -> list[tuple[str, str]]:
        """
        List all (normalized_text, lang) keys for a volume.

        Useful for diagnostics and testing.
        """
        pass
