"""Morphology Service - tokenization and noun extraction for Japanese text."""

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

import dango
from dango.word import PartOfSpeech


@dataclass
class Token:
    """Represents a single morphological token from Japanese text."""

    surface: str
    """Original text (e.g., "走った")"""

    lemma: str
    """Base form from dictionary (e.g., "走る")"""

    pos: str
    """Part of speech as string (noun, verb, etc. from Dango)"""

    reading: str
    """Hiragana reading (e.g., "みました")"""

    start_offset: int
    """Character offset in original text (inclusive)"""

    end_offset: int
    """Character offset in original text (exclusive)"""


class MorphologyService:
    """
    Analyzes Japanese text and extracts morphological information.

    Uses Dango for tokenization, lemmatization, and POS tagging.
    Provides methods to extract specific word types (e.g., nouns) for domain analysis.
    """

    def __init__(self):
        """Initialize the Dango tokenizer."""
        pass  # Dango is stateless; no initialization needed

    def tokenize(self, text: str) -> List[Token]:
        """
        Tokenize Japanese text using Dango.

        Args:
            text: Raw Japanese text from OCR block

        Returns:
            List of Token objects with surface form, lemma, POS, reading, and offsets
        """
        if not text:
            return []

        tokens = []
        current_offset = 0

        try:
            # Dango tokenizes and returns a list of Word objects
            dango_tokens = dango.tokenize(text)

            for dango_token in dango_tokens:
                surface = dango_token.surface
                lemma = dango_token.dictionary_form or surface
                # Convert Dango PartOfSpeech enum to string
                pos = str(dango_token.part_of_speech.name)
                reading = dango_token.surface_reading or surface

                # Calculate offsets
                start_offset = current_offset
                end_offset = current_offset + len(surface)

                tokens.append(
                    Token(
                        surface=surface,
                        lemma=lemma,
                        pos=pos,
                        reading=reading,
                        start_offset=start_offset,
                        end_offset=end_offset,
                    )
                )

                current_offset = end_offset

        except Exception as e:
            print(f"Error tokenizing text '{text}': {e}")
            return []

        return tokens

    def filter_tokens_by_pos(self, tokens: Sequence[Token], allowed_pos: Iterable[str]) -> List[Token]:
        """Return tokens whose POS is in allowed_pos."""
        if not tokens:
            return []

        allowed = set(allowed_pos)
        return [token for token in tokens if token.pos in allowed]

    def extract_words(self, text: str, allowed_pos: Iterable[str]) -> List[Token]:
        """
        Tokenize once and filter by allowed POS values.

        Args:
            text: Raw Japanese text
            allowed_pos: Iterable of POS names to keep

        Returns:
            List of Token objects whose POS is in allowed_pos
        """
        tokens = self.tokenize(text)
        return self.filter_tokens_by_pos(tokens, allowed_pos)

    def extract_nouns(self, text: str) -> List[Token]:
        """
        Extract noun tokens from Japanese text.

        Includes all noun types (common nouns, proper nouns, place names, pronouns).
        Nouns are identified by POS in NOUN, NAME, PLACE_NAME, or PRONOUN.

        Args:
            text: Raw Japanese text

        Returns:
            List of Token objects filtered to nouns only
        """
        return self.extract_words(text, ("NOUN", "NAME", "PLACE_NAME", "PRONOUN"))

    def extract_verbs(self, text: str) -> List[Token]:
        """
        Extract verb tokens (including auxiliary verbs) from Japanese text.

        Args:
            text: Raw Japanese text

        Returns:
            List of Token objects filtered to verbs only
        """
        return self.extract_words(text, ("VERB", "AUXILIARY_VERB"))

    def extract_adjectives(self, text: str) -> List[Token]:
        """
        Extract adjective tokens from Japanese text.

        Includes i-adjectives and na-adjectives (adjectival nouns).

        Args:
            text: Raw Japanese text

        Returns:
            List of Token objects filtered to adjectives only
        """
        return self.extract_words(text, ("ADJECTIVE", "ADJECTIVAL_NOUN"))

    def extract_adverbs(self, text: str) -> List[Token]:
        """
        Extract adverb tokens from Japanese text.

        Args:
            text: Raw Japanese text

        Returns:
            List of Token objects filtered to adverbs only
        """
        return self.extract_words(text, ("ADVERB",))
