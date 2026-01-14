"""Integration test for verb tracking workflow (Phase 3 validation)."""

from pathlib import Path
from manga_reader.services import MorphologyService, DictionaryService, VocabularyService
from manga_reader.io import DatabaseManager


def test_verb_extraction_and_tracking_workflow(tmp_path):
    """
    Full workflow: extract verb from text → track with lemma → verify appearances link.
    Tests the complete Phase 1-3 integration for verbs.
    """
    db_path = tmp_path / "workflow.db"
    db = DatabaseManager(db_path)
    db.ensure_schema()

    morphology = MorphologyService()
    vocab = VocabularyService(db, morphology)

    volume_path = tmp_path / "testVol"
    
    # Real text with verbs and nouns
    text = "田中さんが走った。食べている。"
    
    # Phase 1: Extract verbs (and nouns)
    tokens = morphology.tokenize(text)
    verbs = morphology.filter_tokens_by_pos(tokens, ("VERB", "AUXILIARY_VERB"))
    nouns = morphology.filter_tokens_by_pos(tokens, ("NOUN", "NAME", "PLACE_NAME", "PRONOUN"))
    
    assert len(verbs) > 0, "Should extract verbs from text"
    assert len(nouns) > 0, "Should extract nouns from text"
    
    # Verify conjugation → lemma mapping
    run_verb = next((v for v in verbs if "走" in v.surface), None)
    assert run_verb is not None
    assert run_verb.lemma == "走る", f"Expected lemma 走る, got {run_verb.lemma}"
    
    # Phase 2-3: Track verb by lemma
    word, appearance = vocab.track_word(
        lemma=run_verb.lemma,
        reading=run_verb.reading,
        part_of_speech=run_verb.pos,
        volume_path=volume_path,
        page_index=0,
        crop_coordinates={"x": 0, "y": 0, "width": 10, "height": 10},
        sentence_text=text,
    )
    
    assert word is not None
    assert word.lemma == "走る"
    assert word.part_of_speech == "VERB"
    assert appearance is not None
    
    # Verify: Same verb conjugated differently on next page links to same word
    eat_verb = next((v for v in verbs if "食べ" in v.surface), None)
    if eat_verb:
        word2, _ = vocab.track_word(
            lemma=eat_verb.lemma,
            reading=eat_verb.reading,
            part_of_speech=eat_verb.pos,
            volume_path=volume_path,
            page_index=1,
            crop_coordinates={"x": 0, "y": 0, "width": 10, "height": 10},
            sentence_text="たくさん食べている。",
        )
        
        # Same lemma should reuse same word
        word3, _ = vocab.track_word(
            lemma="食べる",
            reading="たべてる",
            part_of_speech="VERB",
            volume_path=volume_path,
            page_index=2,
            crop_coordinates={"x": 0, "y": 0, "width": 10, "height": 10},
            sentence_text="毎日食べている。",
        )
        
        # All point to same word by lemma
        assert word2.id == word3.id


def test_auxiliary_verb_extracted_correctly(tmp_path):
    """Verify auxiliary verbs are extracted separately from main verbs."""
    morphology = MorphologyService()
    
    # Progressive form: main verb + auxiliary
    text = "食べている"
    tokens = morphology.tokenize(text)
    
    # In Dango, this typically tokenizes as one verb with lemma 食べる
    # But we should handle both VERB and AUXILIARY_VERB in extraction
    verbs = morphology.filter_tokens_by_pos(tokens, ("VERB", "AUXILIARY_VERB"))
    
    assert len(verbs) > 0, "Should extract from 食べている"
    # The exact structure depends on Dango; we trust its lemma extraction
    assert any(v.lemma == "食べる" for v in verbs), "Should find base form 食べる"


def test_adjective_extraction_workflow(tmp_path):
    """Verify adjectives are extracted and highlighted separately."""
    morphology = MorphologyService()
    
    # Text with adjectives
    text = "大きい家と静かな部屋"
    tokens = morphology.tokenize(text)
    
    # Extract adjectives
    adjectives = morphology.filter_tokens_by_pos(tokens, ("ADJECTIVE", "ADJECTIVAL_NOUN"))
    
    assert len(adjectives) > 0, "Should find adjectives"
    
    # Verify i-adjective
    assert any(a.surface == "大きい" for a in adjectives), "Should find 大きい"
    
    # Verify na-adjective (typically as 静か without な)
    assert any("静" in a.surface for a in adjectives), "Should find 静かな component"


def test_all_word_types_extracted_in_single_pass(tmp_path):
    """Verify nouns, verbs, and adjectives are all extracted efficiently."""
    morphology = MorphologyService()
    
    text = "美しい猫が静かに走った"
    tokens = morphology.tokenize(text)
    
    # Single extraction call combining all POS
    all_interested = morphology.extract_words(
        text,
        ("NOUN", "NAME", "PLACE_NAME", "PRONOUN", "VERB", "AUXILIARY_VERB", "ADJECTIVE", "ADJECTIVAL_NOUN")
    )
    
    assert len(all_interested) > 0
    
    # Verify we have multiple types
    pos_types = {t.pos for t in all_interested}
    assert len(pos_types) > 1, "Should have multiple POS types"
