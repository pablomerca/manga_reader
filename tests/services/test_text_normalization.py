"""Unit tests for text normalization."""

import pytest

from manga_reader.services import normalize_text


class TestTextNormalization:
    """Tests for normalize_text function."""

    def test_trim_leading_whitespace(self):
        """Should remove leading whitespace."""
        assert normalize_text("   こんにちは") == "こんにちは"

    def test_trim_trailing_whitespace(self):
        """Should remove trailing whitespace."""
        assert normalize_text("こんにちは   ") == "こんにちは"

    def test_trim_both_sides(self):
        """Should remove whitespace from both sides."""
        assert normalize_text("   こんにちは   ") == "こんにちは"

    def test_collapse_internal_spaces(self):
        """Should collapse multiple spaces to single space."""
        assert normalize_text("hello   world") == "hello world"

    def test_collapse_tabs_to_space(self):
        """Should collapse tabs to single space."""
        assert normalize_text("hello\t\tworld") == "hello world"

    def test_collapse_newlines_to_space(self):
        """Should collapse newlines to single space."""
        assert normalize_text("hello\n\nworld") == "hello world"

    def test_collapse_mixed_whitespace(self):
        """Should collapse mixed whitespace to single space."""
        assert normalize_text("hello \t\n  world") == "hello world"

    def test_multiline_japanese_text(self):
        """Should join multiline Japanese text with single spaces."""
        text = "これは\n複数行の\nテキストです"
        expected = "これは 複数行の テキストです"
        assert normalize_text(text) == expected

    def test_preserve_japanese_characters(self):
        """Should preserve Japanese characters as-is."""
        assert normalize_text("猫が好きです") == "猫が好きです"

    def test_preserve_punctuation(self):
        """Should preserve Japanese punctuation."""
        assert normalize_text("こんにちは！元気ですか？") == "こんにちは！元気ですか？"

    def test_preserve_emoji(self):
        """Should preserve emoji."""
        assert normalize_text("こんにちは 😊") == "こんにちは 😊"

    def test_empty_string(self):
        """Should handle empty string."""
        assert normalize_text("") == ""

    def test_only_whitespace(self):
        """Should collapse whitespace-only string to empty."""
        assert normalize_text("   \t\n   ") == ""

    def test_deterministic_keying(self):
        """Same logical text with different whitespace should normalize to same key."""
        text1 = "こんにちは\n世界"
        text2 = "こんにちは  世界"
        text3 = "こんにちは\t世界"
        
        assert normalize_text(text1) == normalize_text(text2)
        assert normalize_text(text2) == normalize_text(text3)

    def test_ocr_block_with_internal_newlines(self):
        """Should handle typical OCR block structure."""
        ocr_text = "お前は\n何をして\nいるんだ？"
        expected = "お前は 何をして いるんだ？"
        assert normalize_text(ocr_text) == expected

    def test_complex_real_world_example(self):
        """Should handle complex real-world manga text."""
        text = "  \n  やめろ！\n  そんなことを\n  するな！  \n  "
        expected = "やめろ！ そんなことを するな！"
        assert normalize_text(text) == expected
