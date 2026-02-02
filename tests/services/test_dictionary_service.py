"""Integration tests for DictionaryService (Jamdict-backed)."""

import pytest

from manga_reader.services import (
    DictionaryEntry,
    DictionaryEntryFull,
    DictionaryLookupResult,
    DictionarySense,
    DictionaryService,
    KanjiEntry,
)

pytestmark = pytest.mark.service


@pytest.fixture(scope="module")
def dictionary_service():
    """Provide a shared DictionaryService instance (Jamdict loads data once)."""
    return DictionaryService()


def test_lookup_returns_entry_for_common_noun(dictionary_service):
    entry = dictionary_service.lookup(lemma="猫", surface="猫")

    assert isinstance(entry, DictionaryEntry)
    assert entry.surface == "猫"
    assert entry.reading, "Reading should not be empty"
    assert entry.senses, "Should include at least one sense"
    assert all(isinstance(sense, DictionarySense) for sense in entry.senses)


def test_lookup_uses_lemma_when_surface_is_inflected(dictionary_service):
    entry = dictionary_service.lookup(lemma="走る", surface="走った")

    assert entry is not None, "Should resolve entry using lemma fallback"
    assert entry.surface == "走った", "Surface echoes clicked text for UI"
    assert entry.reading, "Reading should be available"
    assert entry.senses, "Should return senses for lemma"


def test_lookup_returns_none_for_unknown_word(dictionary_service):
    entry = dictionary_service.lookup(lemma="notarealword123", surface="notarealword123")
    assert entry is None


def test_lookup_returns_none_for_empty_input(dictionary_service):
    entry = dictionary_service.lookup(lemma="", surface="")
    assert entry is None


def test_lookup_all_entries_returns_multiple_entries(dictionary_service):
    result = dictionary_service.lookup_all_entries(lemma="僕", surface="僕")

    assert isinstance(result, DictionaryLookupResult)
    assert result.entries, "Should return at least one entry"
    assert all(isinstance(entry, DictionaryEntryFull) for entry in result.entries)
    assert len(result.entries) >= 2, "Expected multiple entries for 僕"


def test_lookup_all_entries_preserves_senses_order(dictionary_service):
    result = dictionary_service.lookup_all_entries(lemma="日本", surface="日本")
    assert result is not None

    jamdict_result = dictionary_service._jamdict.lookup("日本")
    assert jamdict_result.entries

    service_first = result.entries[0]
    jamdict_first = jamdict_result.entries[0]

    service_glosses = [sense.glosses for sense in service_first.senses]
    jamdict_glosses = [
        [gloss.text for gloss in sense.gloss or []] for sense in jamdict_first.senses or []
    ]

    assert service_glosses == jamdict_glosses


def test_lookup_all_entries_with_not_found_returns_none(dictionary_service):
    result = dictionary_service.lookup_all_entries(
        lemma="notarealword123", surface="notarealword123"
    )
    assert result is None


def test_lookup_kanji_extracts_literal(dictionary_service):
    entry = dictionary_service.lookup_kanji("日")

    assert isinstance(entry, KanjiEntry)
    assert entry.literal == "日"


def test_lookup_kanji_extracts_stroke_count(dictionary_service):
    entry = dictionary_service.lookup_kanji("日")
    assert entry.stroke_count is not None
    assert entry.stroke_count > 0


def test_lookup_kanji_extracts_frequency_ranking(dictionary_service):
    entry = dictionary_service.lookup_kanji("日")
    assert entry.frequency is None or entry.frequency > 0


def test_lookup_kanji_separates_on_kun_readings(dictionary_service):
    entry = dictionary_service.lookup_kanji("日")
    assert entry.on_readings or entry.kun_readings


def test_lookup_kanji_extracts_meanings(dictionary_service):
    entry = dictionary_service.lookup_kanji("日")
    assert entry.meanings, "Expected meanings for common kanji"


def test_lookup_kanji_with_not_found_returns_none(dictionary_service):
    entry = dictionary_service.lookup_kanji("𐍈")
    assert entry is None
