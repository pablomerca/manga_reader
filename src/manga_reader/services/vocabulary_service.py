"""Vocabulary Service - orchestrates tracking words and appearances."""

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from manga_reader.core import TrackedWord, WordAppearance
from manga_reader.io import DatabaseManager
from manga_reader.services.text_processing import MorphologyService, Token


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

    #TODO: make more efficient
    def is_word_tracked(self, lemma: str) -> bool:
        """Check if a word is already tracked by lemma.
        
        Args:
            lemma: The dictionary base form to check
            
        Returns:
            True if the word is in vocabulary, False otherwise
        """
        tracked_words = self.list_tracked_words()
        return any(w.lemma == lemma for w in tracked_words)

    def track_word(
        self,
        lemma: str,
        reading: str,
        part_of_speech: str,
        volume_path: Path,
        page_index: int,
        crop_coordinates: Dict[str, float],
        sentence_text: str,
    ) -> Tuple[TrackedWord, WordAppearance]:
        """Track a NEW word and record its first appearance.

        Precondition: Word must not already be tracked (fails fast if violated).
        
        For adding appearances to already-tracked words, use add_appearance_if_new() instead.
        
        Returns:
            Tuple of (TrackedWord, WordAppearance) - both are newly created
            
        Raises:
            ValueError: If word is already tracked (precondition violation)
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

    def get_all_tracked_lemmas(self) -> Set[str]:
        """Return set of all tracked lemmas for fast lookup during rendering.
        
        Returns:
            Set of lemma strings (dictionary base forms) that are currently tracked
        """
        tracked = self.list_tracked_words()
        return {word.lemma for word in tracked}

    def add_appearance_if_new(
        self,
        lemma: str,
        volume_path: Path,
        page_index: int,
        crop_coordinates: Dict[str, float],
        sentence_text: str,
    ) -> Optional[WordAppearance]:
        """
        Add appearance for a tracked word if not already recorded.
        
        This method is used during context synchronization to discover
        all occurrences of tracked words in a volume.
        
        Args:
            lemma: The word lemma to add appearance for
            volume_path: Path to the volume directory
            page_index: Zero-indexed page number
            crop_coordinates: Bounding box dict with keys: x, y, w, h
            sentence_text: The sentence or text block containing the word
            
        Returns:
            WordAppearance if added, None if already exists
            
        Raises:
            ValueError: If lemma is not in tracked_words (fail-fast philosophy)
        """
        # Fail fast: check that lemma is tracked
        tracked_words = self.list_tracked_words()
        word = next((w for w in tracked_words if w.lemma == lemma), None)
        
        if word is None:
            raise ValueError(f"Cannot add appearance for untracked lemma: {lemma}")
        
        # Insert appearance (database will raise ValueError if duplicate exists)
        vol = self._db.upsert_volume(volume_path)
        try:
            appearance = self._db.insert_word_appearance(
                word_id=word.id,
                volume_id=vol.id,
                page_index=page_index,
                crop_coordinates=crop_coordinates,
                sentence_text=sentence_text,
            )
            return appearance
        except ValueError:
            # Duplicate appearance already exists, return None
            return None

