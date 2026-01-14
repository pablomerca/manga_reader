from pathlib import Path

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

    # Idempotency: re-inserting same appearance returns same row
    _, appearance2 = service.track_word(
        lemma="Taberu",
        reading="たべる",
        part_of_speech="Verb",
        volume_path=volume_path,
        page_index=3,
        crop_coordinates={"x": 10, "y": 20, "width": 30, "height": 40},
        sentence_text="ご飯を食べる",
    )
    assert appearance2 is not None
    assert appearance.id == appearance2.id


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
    
    # Track base verb
    word1, _ = service.track_word(
        lemma="食べる",
        reading="たべる",
        part_of_speech="VERB",
        volume_path=volume_path,
        page_index=0,
        crop_coordinates={"x": 0, "y": 0, "width": 10, "height": 10},
        sentence_text="ご飯を食べる",
    )

    # Same lemma, different conjugation (past tense) should reuse same tracked word
    word2, _ = service.track_word(
        lemma="食べる",
        reading="たべた",
        part_of_speech="VERB",
        volume_path=volume_path,
        page_index=1,
        crop_coordinates={"x": 0, "y": 0, "width": 10, "height": 10},
        sentence_text="ご飯を食べた",
    )

    # Both should map to same word ID (lemma-based deduplication)
    assert word1.id == word2.id
    assert word1.lemma == word2.lemma == "食べる"

    # But readings might differ; tracking stores actual reading from conjugated form
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
