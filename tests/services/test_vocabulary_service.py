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
