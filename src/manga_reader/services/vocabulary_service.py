"""Vocabulary Service - orchestrates tracking words and appearances."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from manga_reader.core import TrackedWord, WordAppearance
from manga_reader.io import DatabaseManager
from manga_reader.services.morphology_service import MorphologyService, Token


class VocabularyService:
    """Application service for vocabulary tracking.

    Depends on DatabaseManager for persistence and MorphologyService for lemma/reading.
    """

    def __init__(self, db: DatabaseManager, morphology: MorphologyService) -> None:
        self._db = db
        self._morphology = morphology

    def list_tracked_words(self) -> List[TrackedWord]:
        return self._db.list_tracked_words()

    def list_appearances(self, word_id: int) -> List[WordAppearance]:
        return self._db.list_appearances_for_word(word_id)

    def track_word(
        self,
        lemma: str,
        reading: str,
        part_of_speech: str,
        volume_path: Path,
        page_index: int,
        crop_coordinates: Dict[str, float],
        sentence_text: str,
    ) -> Tuple[TrackedWord, Optional[WordAppearance]]:
        """Track a word and record its appearance at the given context.

        Returns the TrackedWord and the (possibly pre-existing) WordAppearance.
        """
        word = self._db.upsert_tracked_word(lemma, reading, part_of_speech)
        vol = self._db.upsert_volume(volume_path)
        appearance = self._db.insert_word_appearance(
            word_id=word.id,
            volume_id=vol.id,
            page_index=page_index,
            crop_coordinates=crop_coordinates,
            sentence_text=sentence_text,
        )
        return word, appearance

    def track_word_from_surface(
        self,
        surface_text: str,
        volume_path: Path,
        page_index: int,
        crop_coordinates: Dict[str, float],
        sentence_text: str,
    ) -> Tuple[Optional[TrackedWord], Optional[WordAppearance]]:
        """Convenience: derive lemma/reading/POS from surface text then track."""
        tokens: List[Token] = self._morphology.tokenize(surface_text)
        if not tokens:
            return None, None
        token = tokens[0]
        return self.track_word(
            lemma=token.lemma,
            reading=token.reading,
            part_of_speech=token.pos,
            volume_path=volume_path,
            page_index=page_index,
            crop_coordinates=crop_coordinates,
            sentence_text=sentence_text,
        )
