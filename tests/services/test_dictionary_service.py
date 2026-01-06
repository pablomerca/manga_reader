"""Integration tests for DictionaryService (Jamdict-backed)."""

import pytest

from manga_reader.services import DictionaryService, DictionaryEntry, DictionarySense

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
