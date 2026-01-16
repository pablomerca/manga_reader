from pathlib import Path

import pytest

from manga_reader.io import DatabaseManager
from manga_reader.services import VocabularyService


class FakeMorphology:
    def tokenize(self, text: str):
        class T:
            def __init__(self, surface, lemma, pos, reading):
                self.surface = surface
                self.lemma = lemma
                self.pos = pos
                self.reading = reading
        # Return a single token with predictable fields
        return [T(surface=text, lemma=text.lower(), pos="NOUN", reading=text)] if text else []


def test_track_word_and_appearance(tmp_path):
    db_path = tmp_path / "vocab.db"
    db = DatabaseManager(db_path)
    db.ensure_schema()

    service = VocabularyService(db, FakeMorphology())

    volume_path = tmp_path / "vol"
    word, appearance = service.track_word(
        lemma="Taberu",
        reading="たべる",
        part_of_speech="Verb",
        volume_path=volume_path,
        page_index=3,
        crop_coordinates={"x": 10, "y": 20, "width": 30, "height": 40},
        sentence_text="ご飯を食べる",
    )

    assert word.id is not None
    assert appearance is not None
    assert appearance.page_index == 3

    # For duplicate appearances of already-tracked word, use add_appearance_if_new
    appearance2 = service.add_appearance_if_new(
        lemma="Taberu",
        volume_path=volume_path,
        page_index=3,
        crop_coordinates={"x": 10, "y": 20, "width": 30, "height": 40},
        sentence_text="ご飯を食べる",
    )
    assert appearance2 is None  # Duplicate appearance, so None returned


def test_track_word_from_surface_uses_morphology(tmp_path):
    db = DatabaseManager(tmp_path / "vocab2.db")
    db.ensure_schema()

    service = VocabularyService(db, FakeMorphology())

    vol = tmp_path / "vol2"
    word, appearance = service.track_word_from_surface(
        surface_text="NEKO",
        volume_path=vol,
        page_index=0,
        crop_coordinates={"x": 1, "y": 2, "width": 3, "height": 4},
        sentence_text="猫が走った",
    )

    assert word is not None
    assert word.lemma == "neko"
    assert word.reading == "NEKO"
    assert appearance is not None
    assert appearance.page_index == 0


def test_track_verb_with_conjugations(tmp_path):
    """Test tracking a verb with different conjugated forms."""
    db_path = tmp_path / "vocab_verb.db"
    db = DatabaseManager(db_path)
    db.ensure_schema()

    service = VocabularyService(db, FakeMorphology())

    volume_path = tmp_path / "vol"
    
    # Track base verb (first appearance)
    word1, _ = service.track_word(
        lemma="食べる",
        reading="たべる",
        part_of_speech="VERB",
        volume_path=volume_path,
        page_index=0,
        crop_coordinates={"x": 0, "y": 0, "width": 10, "height": 10},
        sentence_text="ご飯を食べる",
    )

    # Same lemma, different conjugation (past tense) - add as new appearance
    appearance2 = service.add_appearance_if_new(
        lemma="食べる",
        volume_path=volume_path,
        page_index=1,
        crop_coordinates={"x": 0, "y": 0, "width": 10, "height": 10},
        sentence_text="ご飯を食べた",
    )

    # Both appearances should map to same word ID (lemma-based deduplication)
    assert appearance2 is not None
    assert word1.lemma == "食べる"

    # Tracking stores actual reading from conjugated form
    appearances = service.list_appearances(word1.id)
    assert len(appearances) == 2
    assert appearances[0].page_index == 0
    assert appearances[1].page_index == 1


def test_track_auxiliary_verb(tmp_path):
    """Test tracking an auxiliary verb separately from main verb."""
    db_path = tmp_path / "vocab_aux.db"
    db = DatabaseManager(db_path)
    db.ensure_schema()

    service = VocabularyService(db, FakeMorphology())
    volume_path = tmp_path / "vol"

    # Track auxiliary verb
    word, _ = service.track_word(
        lemma="いる",
        reading="いる",
        part_of_speech="AUXILIARY_VERB",
        volume_path=volume_path,
        page_index=0,
        crop_coordinates={"x": 0, "y": 0, "width": 10, "height": 10},
        sentence_text="食べている",
    )

    assert word.part_of_speech == "AUXILIARY_VERB"
    assert word.lemma == "いる"

def test_get_all_tracked_lemmas_returns_set(tmp_path):
    """Test get_all_tracked_lemmas returns a set of all tracked lemmas."""
    db = DatabaseManager(tmp_path / "vocab_lemmas.db")
    db.ensure_schema()
    
    service = VocabularyService(db, FakeMorphology())
    
    # Initially empty
    lemmas = service.get_all_tracked_lemmas()
    assert lemmas == set()
    
    # Track multiple words
    service.track_word(
        lemma="食べる",
        reading="たべる",
        part_of_speech="VERB",
        volume_path=tmp_path / "vol",
        page_index=0,
        crop_coordinates={"x": 0, "y": 0, "width": 10, "height": 10},
        sentence_text="食べた",
    )
    
    service.track_word(
        lemma="走る",
        reading="はしる",
        part_of_speech="VERB",
        volume_path=tmp_path / "vol",
        page_index=1,
        crop_coordinates={"x": 0, "y": 0, "width": 10, "height": 10},
        sentence_text="走った",
    )
    
    service.track_word(
        lemma="猫",
        reading="ねこ",
        part_of_speech="NOUN",
        volume_path=tmp_path / "vol",
        page_index=2,
        crop_coordinates={"x": 0, "y": 0, "width": 10, "height": 10},
        sentence_text="猫が走った",
    )
    
    # Get all lemmas
    lemmas = service.get_all_tracked_lemmas()
    assert lemmas == {"食べる", "走る", "猫"}


def test_add_appearance_if_new_raises_for_untracked_lemma(tmp_path):
    """Test add_appearance_if_new raises ValueError for untracked lemma."""
    db = DatabaseManager(tmp_path / "vocab_untracked.db")
    db.ensure_schema()
    
    service = VocabularyService(db, FakeMorphology())
    
    # Try to add appearance for untracked word
    with pytest.raises(ValueError, match="Cannot add appearance for untracked lemma"):
        service.add_appearance_if_new(
            lemma="存在しない",
            volume_path=tmp_path / "vol",
            page_index=0,
            crop_coordinates={"x": 0, "y": 0, "width": 10, "height": 10},
            sentence_text="この言葉は存在しない",
        )


def test_add_appearance_if_new_succeeds_for_tracked_word(tmp_path):
    """Test add_appearance_if_new succeeds when lemma is tracked."""
    db = DatabaseManager(tmp_path / "vocab_new_app.db")
    db.ensure_schema()
    
    service = VocabularyService(db, FakeMorphology())
    
    # First, track the word
    word, initial_appearance = service.track_word(
        lemma="食べる",
        reading="たべる",
        part_of_speech="VERB",
        volume_path=tmp_path / "vol",
        page_index=0,
        crop_coordinates={"x": 0, "y": 0, "width": 10, "height": 10},
        sentence_text="食べた",
    )
    
    # Now add another appearance
    appearance = service.add_appearance_if_new(
        lemma="食べる",
        volume_path=tmp_path / "vol",
        page_index=1,
        crop_coordinates={"x": 20, "y": 30, "width": 50, "height": 60},
        sentence_text="ご飯を食べます",
    )
    
    assert appearance is not None
    assert appearance.page_index == 1
    assert appearance.crop_coordinates["x"] == 20
    
    # Verify both appearances exist
    appearances = service.list_appearances(word.id)
    assert len(appearances) == 2


def test_add_appearance_if_new_returns_existing_for_duplicate(tmp_path):
    """Test add_appearance_if_new returns existing appearance for duplicate (already exists)."""
    db = DatabaseManager(tmp_path / "vocab_dup.db")
    db.ensure_schema()
    
    service = VocabularyService(db, FakeMorphology())
    
    # Track word with first appearance
    word, initial_appearance = service.track_word(
        lemma="食べる",
        reading="たべる",
        part_of_speech="VERB",
        volume_path=tmp_path / "vol",
        page_index=0,
        crop_coordinates={"x": 0, "y": 0, "width": 10, "height": 10},
        sentence_text="食べた",
    )
    
    # Try to add exact same appearance
    appearance = service.add_appearance_if_new(
        lemma="食べる",
        volume_path=tmp_path / "vol",
        page_index=0,
        crop_coordinates={"x": 0, "y": 0, "width": 10, "height": 10},
        sentence_text="食べた",
    )
    
    # Should return None because duplicate already exists (ValueError caught internally)
    assert appearance is None
    
    # Still only one appearance
    appearances = service.list_appearances(word.id)
    assert len(appearances) == 1