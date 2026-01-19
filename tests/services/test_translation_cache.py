"""Unit tests for TranslationCache abstraction."""

from datetime import datetime

import pytest

from manga_reader.services import InMemoryTranslationCache, CacheRecord


@pytest.fixture
def cache():
    """Provide a fresh cache instance for each test."""
    return InMemoryTranslationCache()


class TestInMemoryTranslationCacheContract:
    """Tests validating TranslationCache abstraction contract."""

    def test_get_returns_none_for_nonexistent_entry(self, cache):
        """Cache should return None when entry does not exist."""
        result = cache.get(
            volume_id="vol1", normalized_text="こんにちは", lang="en"
        )
        assert result is None

    def test_put_and_get_roundtrip(self, cache):
        """Cache should store and retrieve entries correctly."""
        record = CacheRecord(
            normalized_text="こんにちは",
            lang="en",
            translation="Hello",
            explanation="Polite greeting",
            model="gemini-pro",
            updated_at=datetime.now(),
        )

        cache.put(
            volume_id="vol1",
            normalized_text="こんにちは",
            lang="en",
            record=record,
        )

        retrieved = cache.get(volume_id="vol1", normalized_text="こんにちは", lang="en")
        assert retrieved is not None
        assert retrieved.translation == "Hello"
        assert retrieved.explanation == "Polite greeting"

    def test_put_overwrites_existing_entry(self, cache):
        """Putting the same key should overwrite."""
        record1 = CacheRecord(
            normalized_text="猫",
            lang="en",
            translation="cat (old)",
            explanation=None,
            model="gemini-pro",
            updated_at=datetime.now(),
        )
        cache.put(volume_id="vol1", normalized_text="猫", lang="en", record=record1)

        record2 = CacheRecord(
            normalized_text="猫",
            lang="en",
            translation="cat (new)",
            explanation="A feline animal",
            model="gemini-pro",
            updated_at=datetime.now(),
        )
        cache.put(volume_id="vol1", normalized_text="猫", lang="en", record=record2)

        retrieved = cache.get(volume_id="vol1", normalized_text="猫", lang="en")
        assert retrieved.translation == "cat (new)"
        assert retrieved.explanation == "A feline animal"

    def test_delete_removes_entry(self, cache):
        """Deleting an entry should remove it."""
        record = CacheRecord(
            normalized_text="水",
            lang="en",
            translation="water",
            explanation=None,
            model="gemini-pro",
            updated_at=datetime.now(),
        )
        cache.put(volume_id="vol1", normalized_text="水", lang="en", record=record)

        cache.delete(volume_id="vol1", normalized_text="水", lang="en")
        result = cache.get(volume_id="vol1", normalized_text="水", lang="en")
        assert result is None

    def test_delete_nonexistent_entry_does_not_raise(self, cache):
        """Deleting a non-existent entry should not raise."""
        cache.delete(volume_id="vol1", normalized_text="nonexistent", lang="en")
        # No exception should be raised

    def test_clear_volume_removes_all_entries_for_volume(self, cache):
        """Clearing a volume should remove all its entries."""
        record1 = CacheRecord(
            normalized_text="猫",
            lang="en",
            translation="cat",
            explanation=None,
            model="gemini-pro",
            updated_at=datetime.now(),
        )
        record2 = CacheRecord(
            normalized_text="犬",
            lang="en",
            translation="dog",
            explanation=None,
            model="gemini-pro",
            updated_at=datetime.now(),
        )

        cache.put(volume_id="vol1", normalized_text="猫", lang="en", record=record1)
        cache.put(volume_id="vol1", normalized_text="犬", lang="en", record=record2)

        cache.clear_volume("vol1")

        assert cache.get(volume_id="vol1", normalized_text="猫", lang="en") is None
        assert cache.get(volume_id="vol1", normalized_text="犬", lang="en") is None

    def test_different_volumes_are_isolated(self, cache):
        """Entries in different volumes should not interfere."""
        record1 = CacheRecord(
            normalized_text="猫",
            lang="en",
            translation="cat (vol1)",
            explanation=None,
            model="gemini-pro",
            updated_at=datetime.now(),
        )
        record2 = CacheRecord(
            normalized_text="猫",
            lang="en",
            translation="cat (vol2)",
            explanation=None,
            model="gemini-pro",
            updated_at=datetime.now(),
        )

        cache.put(volume_id="vol1", normalized_text="猫", lang="en", record=record1)
        cache.put(volume_id="vol2", normalized_text="猫", lang="en", record=record2)

        result1 = cache.get(volume_id="vol1", normalized_text="猫", lang="en")
        result2 = cache.get(volume_id="vol2", normalized_text="猫", lang="en")

        assert result1.translation == "cat (vol1)"
        assert result2.translation == "cat (vol2)"

    def test_different_languages_are_isolated(self, cache):
        """Entries with different language codes should be separate."""
        record_en = CacheRecord(
            normalized_text="こんにちは",
            lang="en",
            translation="Hello",
            explanation=None,
            model="gemini-pro",
            updated_at=datetime.now(),
        )
        record_fr = CacheRecord(
            normalized_text="こんにちは",
            lang="fr",
            translation="Bonjour",
            explanation=None,
            model="gemini-pro",
            updated_at=datetime.now(),
        )

        cache.put(
            volume_id="vol1",
            normalized_text="こんにちは",
            lang="en",
            record=record_en,
        )
        cache.put(
            volume_id="vol1",
            normalized_text="こんにちは",
            lang="fr",
            record=record_fr,
        )

        result_en = cache.get(volume_id="vol1", normalized_text="こんにちは", lang="en")
        result_fr = cache.get(volume_id="vol1", normalized_text="こんにちは", lang="fr")

        assert result_en.translation == "Hello"
        assert result_fr.translation == "Bonjour"

    def test_list_keys_returns_all_keys_for_volume(self, cache):
        """list_keys should return all (normalized_text, lang) pairs for a volume."""
        record1 = CacheRecord(
            normalized_text="猫",
            lang="en",
            translation="cat",
            explanation=None,
            model="gemini-pro",
            updated_at=datetime.now(),
        )
        record2 = CacheRecord(
            normalized_text="犬",
            lang="en",
            translation="dog",
            explanation=None,
            model="gemini-pro",
            updated_at=datetime.now(),
        )

        cache.put(volume_id="vol1", normalized_text="猫", lang="en", record=record1)
        cache.put(volume_id="vol1", normalized_text="犬", lang="en", record=record2)

        keys = cache.list_keys("vol1")
        assert len(keys) == 2
        assert ("猫", "en") in keys
        assert ("犬", "en") in keys

    def test_list_keys_empty_for_nonexistent_volume(self, cache):
        """list_keys should return empty list for volume with no entries."""
        keys = cache.list_keys("nonexistent_vol")
        assert keys == []

    def test_cache_record_contains_all_fields(self, cache):
        """CacheRecord should preserve all fields (translation, explanation, etc.)."""
        record = CacheRecord(
            normalized_text="走っている",
            lang="en",
            translation="is running",
            explanation="Present progressive form of 走る (to run)",
            model="gemini-1.5-pro",
            updated_at=datetime(2026, 1, 19, 12, 30, 0),
        )

        cache.put(
            volume_id="vol1",
            normalized_text="走っている",
            lang="en",
            record=record,
        )

        retrieved = cache.get(volume_id="vol1", normalized_text="走っている", lang="en")
        assert retrieved.translation == "is running"
        assert retrieved.explanation == "Present progressive form of 走る (to run)"
        assert retrieved.model == "gemini-1.5-pro"
        assert retrieved.updated_at == datetime(2026, 1, 19, 12, 30, 0)

    def test_cache_record_allows_none_translation(self, cache):
        """CacheRecord should allow None for translation (explanation-only entries)."""
        record = CacheRecord(
            normalized_text="猫",
            lang="en",
            translation=None,
            explanation="A feline animal",
            model="gemini-pro",
            updated_at=datetime.now(),
        )

        cache.put(volume_id="vol1", normalized_text="猫", lang="en", record=record)
        retrieved = cache.get(volume_id="vol1", normalized_text="猫", lang="en")
        assert retrieved.translation is None
        assert retrieved.explanation is not None

    def test_cache_record_allows_none_explanation(self, cache):
        """CacheRecord should allow None for explanation (translation-only entries)."""
        record = CacheRecord(
            normalized_text="猫",
            lang="en",
            translation="cat",
            explanation=None,
            model="gemini-pro",
            updated_at=datetime.now(),
        )

        cache.put(volume_id="vol1", normalized_text="猫", lang="en", record=record)
        retrieved = cache.get(volume_id="vol1", normalized_text="猫", lang="en")
        assert retrieved.translation is not None
        assert retrieved.explanation is None
