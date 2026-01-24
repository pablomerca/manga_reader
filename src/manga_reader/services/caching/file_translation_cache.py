"""File-based translation cache implementation for per-volume persistent storage."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from manga_reader.services.caching.translation_cache import CacheRecord, TranslationCache


class FileTranslationCache(TranslationCache):
    """
    File-based cache implementation storing translations per volume.

    Cache files are stored alongside the .mokuro file in each volume directory
    as `.translations-cache.json`.

    Format:
    {
        "version": 1,
        "volume_id": "<volume-path>",
        "entries": [
            {
                "normalized_text": "...",
                "lang": "en",
                "translation": "...",
                "explanation": "...",
                "model": "gemini-xxx",
                "updated_at": "2026-01-19T12:34:56Z"
            }
        ]
    }
    """

    CACHE_VERSION = 1
    CACHE_FILENAME = ".translations-cache.json"

    def __init__(self):
        self._in_memory_lru: dict[str, dict[tuple[str, str], CacheRecord]] = {}
        self._max_lru_size = 100

    def get(
        self, volume_id: str, normalized_text: str, lang: str = "en"
    ) -> Optional[CacheRecord]:
        """Retrieve cached entry, checking in-memory LRU first, then file."""
        key = (normalized_text, lang)
        
        if volume_id in self._in_memory_lru:
            if key in self._in_memory_lru[volume_id]:
                return self._in_memory_lru[volume_id][key]
        
        cache_file = self._get_cache_file_path(volume_id)
        if not cache_file.exists():
            return None
        
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            
            for entry in data.get("entries", []):
                if (
                    entry["normalized_text"] == normalized_text
                    and entry["lang"] == lang
                ):
                    record = CacheRecord(
                        normalized_text=entry["normalized_text"],
                        lang=entry["lang"],
                        translation=entry.get("translation"),
                        explanation=entry.get("explanation"),
                        model=entry["model"],
                        updated_at=datetime.fromisoformat(entry["updated_at"]),
                    )
                    self._add_to_lru(volume_id, key, record)
                    return record
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error reading cache file {cache_file}: {e}")
            return None
        
        return None

    def put(
        self,
        volume_id: str,
        normalized_text: str,
        lang: str,
        record: CacheRecord,
    ) -> None:
        """Store or update a cache entry in both LRU and file."""
        key = (normalized_text, lang)
        self._add_to_lru(volume_id, key, record)
        
        cache_file = self._get_cache_file_path(volume_id)
        
        try:
            if cache_file.exists():
                data = json.loads(cache_file.read_text(encoding="utf-8"))
            else:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                data = {
                    "version": self.CACHE_VERSION,
                    "volume_id": volume_id,
                    "entries": [],
                }
            
            entries = data.get("entries", [])
            existing_idx = None
            for idx, entry in enumerate(entries):
                if (
                    entry["normalized_text"] == normalized_text
                    and entry["lang"] == lang
                ):
                    existing_idx = idx
                    break
            
            entry_data = {
                "normalized_text": record.normalized_text,
                "lang": record.lang,
                "translation": record.translation,
                "explanation": record.explanation,
                "model": record.model,
                "updated_at": record.updated_at.isoformat(),
            }
            
            if existing_idx is not None:
                entries[existing_idx] = entry_data
            else:
                entries.append(entry_data)
            
            data["entries"] = entries
            cache_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error writing cache file {cache_file}: {e}")

    def delete(
        self, volume_id: str, normalized_text: str, lang: str = "en"
    ) -> None:
        """Delete a single cache entry."""
        key = (normalized_text, lang)
        
        if volume_id in self._in_memory_lru:
            self._in_memory_lru[volume_id].pop(key, None)
        
        cache_file = self._get_cache_file_path(volume_id)
        if not cache_file.exists():
            return
        
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            entries = data.get("entries", [])
            entries = [
                e
                for e in entries
                if not (e["normalized_text"] == normalized_text and e["lang"] == lang)
            ]
            data["entries"] = entries
            cache_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error deleting from cache file {cache_file}: {e}")

    def clear_volume(self, volume_id: str) -> None:
        """Clear all cache entries for a volume."""
        self._in_memory_lru.pop(volume_id, None)
        
        cache_file = self._get_cache_file_path(volume_id)
        if cache_file.exists():
            try:
                cache_file.unlink()
            except OSError as e:
                print(f"Error deleting cache file {cache_file}: {e}")

    def list_keys(self, volume_id: str) -> list[tuple[str, str]]:
        """List all (normalized_text, lang) keys for a volume."""
        cache_file = self._get_cache_file_path(volume_id)
        if not cache_file.exists():
            return []
        
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return [
                (entry["normalized_text"], entry["lang"])
                for entry in data.get("entries", [])
            ]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error reading cache file {cache_file}: {e}")
            return []

    def _get_cache_file_path(self, volume_id: str) -> Path:
        """Get the cache file path for a given volume."""
        volume_path = Path(volume_id)
        return volume_path / self.CACHE_FILENAME

    def _add_to_lru(
        self, volume_id: str, key: tuple[str, str], record: CacheRecord
    ) -> None:
        """Add entry to in-memory LRU cache."""
        if volume_id not in self._in_memory_lru:
            self._in_memory_lru[volume_id] = {}
        
        self._in_memory_lru[volume_id][key] = record
        
        if len(self._in_memory_lru[volume_id]) > self._max_lru_size:
            first_key = next(iter(self._in_memory_lru[volume_id]))
            del self._in_memory_lru[volume_id][first_key]
