"""Unit tests for MorphologyService."""

from typing import List
import pytest

from manga_reader.services import MorphologyService, Token


@pytest.fixture
def morphology_service():
    """Fixture to provide a fresh MorphologyService instance."""
    return MorphologyService()


class TestTokenize:
    """Tests for MorphologyService.tokenize() method."""

    def test_tokenize_simple_sentence(self, morphology_service):
        """Test tokenization of a simple Japanese sentence."""
        text = "猫が走った"
        tokens = morphology_service.tokenize(text)

        assert len(tokens) > 0, "Should tokenize non-empty text"
        assert all(isinstance(t, Token) for t in tokens), "All results should be Token objects"

    def test_tokenize_empty_string(self, morphology_service):
        """Test tokenization of empty string returns empty list."""
        tokens = morphology_service.tokenize("")
        assert tokens == [], "Empty text should return empty list"

    def test_tokenize_offset_accuracy(self, morphology_service):
        """Test that token offsets correctly map to original text."""
        text = "猫が走った"
        tokens = morphology_service.tokenize(text)

        for token in tokens:
            # Verify offsets are within bounds
            assert 0 <= token.start_offset <= len(text)
            assert 0 <= token.end_offset <= len(text)
            assert token.start_offset <= token.end_offset

            # Verify substring matches surface form
            original_substring = text[token.start_offset : token.end_offset]
            assert original_substring == token.surface, (
                f"Offset mismatch: text[{token.start_offset}:{token.end_offset}] = "
                f"'{original_substring}' != '{token.surface}'"
            )

    def test_tokenize_has_pos(self, morphology_service):
        """Test that all tokens have POS tags."""
        text = "日本の漫画"
        tokens = morphology_service.tokenize(text)

        assert all(token.pos for token in tokens), "All tokens should have POS tags"

    def test_tokenize_has_reading(self, morphology_service):
        """Test that tokens have reading information."""
        text = "走る"
        tokens = morphology_service.tokenize(text)

        assert all(token.reading for token in tokens), "All tokens should have reading"

    def test_tokenize_has_lemma(self, morphology_service):
        """Test that tokens have lemma (dictionary form)."""
        text = "走った"
        tokens = morphology_service.tokenize(text)

        # At least some tokens should have lemmas
        assert any(token.lemma for token in tokens), "Tokens should have lemmas"


class TestExtractNouns:
    """Tests for MorphologyService.extract_nouns() method."""

    def test_extract_nouns_filters_correctly(self, morphology_service):
        """Test that extract_nouns returns only nouns."""
        text = "田中さんは走った。"
        nouns : List[Token] = morphology_service.extract_nouns(text)

        # All results should be nouns (including names, place names, and pronouns)
        assert all(
            noun.pos in ("NOUN", "NAME", "PLACE_NAME", "PRONOUN") for noun in nouns
        ), "All results should be nouns, names, or pronouns (POS in ['NOUN', 'NAME', 'PLACE_NAME', 'PRONOUN'])"

    def test_extract_nouns_common_noun(self, morphology_service):
        """Test extraction of common nouns."""
        text = "猫です"
        nouns = morphology_service.extract_nouns(text)

        # Should find "猫" (cat) as a common noun
        assert any(n.surface == "猫" for n in nouns), "Should find 猫 as a noun"

    def test_extract_nouns_proper_noun(self, morphology_service):
        """Test extraction of proper nouns."""
        text = "田中さん"
        nouns = morphology_service.extract_nouns(text)

        # Should find "田中" (proper noun)
        noun_surfaces = [n.surface for n in nouns]
        assert "田中" in noun_surfaces, (
            "Should find 田中 as a noun"
        )

    def test_extract_nouns_empty_when_no_nouns(self, morphology_service):
        """Test that extract_nouns returns empty list when no nouns present."""
        text = "走った。"  # Only verb + punctuation
        nouns = morphology_service.extract_nouns(text)

        assert len(nouns) == 0, "Text with no nouns should return empty list"

    def test_extract_nouns_empty_string(self, morphology_service):
        """Test extraction from empty string returns empty list."""
        nouns = morphology_service.extract_nouns("")
        assert nouns == [], "Empty text should return empty list"

    def test_extract_nouns_preserves_offsets(self, morphology_service):
        """Test that noun offsets are correct and can be used to extract text."""
        text = "公園の猫は走った"
        nouns = morphology_service.extract_nouns(text)

        # Verify each noun's offsets map correctly to original text
        for noun in nouns:
            extracted_text = text[noun.start_offset : noun.end_offset]
            assert extracted_text == noun.surface, (
                f"Noun offset mismatch: text[{noun.start_offset}:{noun.end_offset}] = "
                f"'{extracted_text}' != '{noun.surface}'"
            )

    def test_extract_nouns_multiple_sentences(self, morphology_service):
        """Test extraction from multiple sentences."""
        text = "猫が走った。犬も走った。"
        nouns = morphology_service.extract_nouns(text)

        # Should find "猫" and "犬" as nouns
        noun_surfaces = [n.surface for n in nouns]
        assert "猫" in noun_surfaces, "Should find 猫"
        assert "犬" in noun_surfaces, "Should find 犬"

    def test_extract_nouns_with_punctuation_and_mixed_script(self, morphology_service):
        """Test extraction from sentence with punctuation and hiragana/kanji mix."""
        text = "物体を映像でかくにん確認！！"
        nouns = morphology_service.extract_nouns(text)

        # Expected nouns: 物体, 映像, かくにん, 確認
        expected_nouns = ["物体", "映像", "かくにん", "確認"]
        extracted_surfaces = [n.surface for n in nouns]

        for expected in expected_nouns:
            assert expected in extracted_surfaces, (
                f"Should find '{expected}' as a noun. Found: {extracted_surfaces}"
            )

    def test_extract_nouns_with_spaces_and_compound_subjects(self, morphology_service):
        """Test extraction from sentence with spaces and plural subjects.
        
        Note: 僕ら gets split into 僕 (noun) + ら (suffix), so we expect only 僕.
        """
        text = "さっき僕らを 助けてくれた ロボット！？"
        nouns = morphology_service.extract_nouns(text)

        # Expected nouns: さっき, 僕, ロボット
        # (僕ら splits into 僕 + ら where ら is a suffix, not a noun)
        expected_nouns = ["さっき", "僕", "ロボット"]
        extracted_surfaces = [n.surface for n in nouns]

        for expected in expected_nouns:
            assert expected in extracted_surfaces, (
                f"Should find '{expected}' as a noun. Found: {extracted_surfaces}"
            )


class TestExtractVerbs:
    """Tests for MorphologyService.extract_verbs() method."""

    def test_extract_verbs_filters_correctly(self, morphology_service):
        """extract_verbs returns only verbs or auxiliary verbs."""
        text = "猫が走った。食べている。"
        verbs = morphology_service.extract_verbs(text)

        assert all(v.pos in ("VERB", "AUXILIARY_VERB") for v in verbs)

    def test_extract_verbs_handles_conjugations(self, morphology_service):
        """Conjugated verbs should report lemma in dictionary form."""
        text = "食べました"
        verbs = morphology_service.extract_verbs(text)

        assert any(v.lemma == "食べる" for v in verbs)

    def test_extract_verbs_empty_when_no_verbs(self, morphology_service):
        """Text without verbs should return empty list."""
        text = "猫と犬"
        verbs = morphology_service.extract_verbs(text)

        assert verbs == []


class TestExtractAdjectives:
    """Tests for MorphologyService.extract_adjectives() method."""

    def test_extract_adjectives_filters_correctly(self, morphology_service):
        """extract_adjectives returns only adjectives or adjectival nouns."""
        text = "大きい猫、静かな部屋"
        adjectives = morphology_service.extract_adjectives(text)

        assert all(a.pos in ("ADJECTIVE", "ADJECTIVAL_NOUN") for a in adjectives)

    def test_extract_adjectives_handles_i_adjectives(self, morphology_service):
        """Extract i-adjectives (e.g., 大きい)."""
        text = "大きい"
        adjectives = morphology_service.extract_adjectives(text)

        assert len(adjectives) > 0
        assert any(a.surface == "大きい" for a in adjectives)

    def test_extract_adjectives_handles_na_adjectives(self, morphology_service):
        """Extract na-adjectives (e.g., 静か in 静かな)."""
        text = "静かな"
        adjectives = morphology_service.extract_adjectives(text)

        # 静かな typically tokenizes as 静か (ADJECTIVAL_NOUN) + な (auxiliary)
        # We should find 静か with ADJECTIVAL_NOUN POS
        assert any(a.pos == "ADJECTIVAL_NOUN" for a in adjectives)

    def test_extract_adjectives_empty_when_no_adjectives(self, morphology_service):
        """Text without adjectives should return empty list."""
        text = "猫が走った"
        adjectives = morphology_service.extract_adjectives(text)

        assert adjectives == []


class TestTokenProperties:
    """Tests for Token dataclass properties."""

    def test_token_creation(self):
        """Test creating a Token instance."""
        token = Token(
            surface="走った",
            lemma="走る",
            pos="VERB",
            reading="はしった",
            start_offset=0,
            end_offset=3,
        )

        assert token.surface == "走った"
        assert token.lemma == "走る"
        assert token.pos == "VERB"
        assert token.reading == "はしった"
        assert token.start_offset == 0
        assert token.end_offset == 3

    def test_token_fields_exist(self):
        """Test that Token has all expected fields."""
        token = Token(
            surface="猫",
            lemma="猫",
            pos="NOUN",
            reading="ねこ",
            start_offset=0,
            end_offset=1,
        )

        assert hasattr(token, "surface")
        assert hasattr(token, "lemma")
        assert hasattr(token, "pos")
        assert hasattr(token, "reading")
        assert hasattr(token, "start_offset")
        assert hasattr(token, "end_offset")

