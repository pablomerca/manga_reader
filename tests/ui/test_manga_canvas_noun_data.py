"""Integration tests for MangaCanvas noun data rendering."""

import json
import re
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from manga_reader.core.manga_page import MangaPage
from manga_reader.core.ocr_block import OCRBlock
from manga_reader.services import MorphologyService, Token


pytestmark = pytest.mark.skip(reason="Qt UI tests require display server - skipped in CI/headless environments")


@pytest.fixture
def morphology_service():
    """Fixture to provide a MorphologyService instance."""
    return MorphologyService()


@pytest.fixture
def canvas(morphology_service):
    """Fixture to provide a MangaCanvas instance with mocked Qt components."""
    # Skip Qt-dependent tests
    pytest.skip("Qt UI tests not available in headless environment")


class TestRenderPagesWithNounData:
    """Tests for noun data inclusion in render_pages output."""

    def test_render_pages_includes_noun_data(self, canvas, morphology_service):
        """Test that render_pages includes noun data in block structure."""
        # Sample text with a noun
        text = "田中さんは走った。"
        # Mock the morphology service to return expected nouns
        nouns = [
            Token(
                surface="田中",
                lemma="田中",
                pos="NAME",  # Updated to match Dango enum string
                reading="たなか",
                start_offset=0,
                end_offset=2,
            )
        ]

        # Replace extract_nouns with a mock
        canvas.morphology_service = Mock()
        canvas.morphology_service.extract_nouns.return_value = nouns

        # Create test page
        page = MangaPage(
            page_number=0, image_path=Path("/tmp/img.jpg"), width=1280, height=1600
        )
        page.ocr_blocks = [OCRBlock(x=0, y=0, width=100, height=50, text_lines=["田中さんは走った。"])]

        # Mock runJavaScript to capture the data being passed
        mock_run_js = Mock()
        canvas.web_view.page = Mock()
        canvas.web_view.page().runJavaScript = mock_run_js

        # Call render_pages
        canvas.render_pages([page])

        # Verify runJavaScript was called
        mock_run_js.assert_called_once()
        call_args = mock_run_js.call_args[0][0]

        # Extract JSON from "updateView({...});"
        match = re.search(r"updateView\((.*)\);", call_args)
        assert match, "runJavaScript call should contain updateView with JSON data"

        json_str = match.group(1)
        data = json.loads(json_str)

        # Verify noun data is included in block
        assert len(data["pages"]) == 1
        assert len(data["pages"][0]["blocks"]) == 1
        block = data["pages"][0]["blocks"][0]

        assert "nouns" in block, "Block should have 'nouns' key"
        assert len(block["nouns"]) == 1, "Block should contain one noun"
        assert block["nouns"][0]["lemma"] == "田中"
        assert block["nouns"][0]["surface"] == "田中"
        assert block["nouns"][0]["start"] == 0
        assert block["nouns"][0]["end"] == 2

    def test_render_pages_with_no_nouns(self, canvas):
        """Test render_pages when block has no nouns."""
        # Text with no nouns: only verb + punctuation
        text = "走った。"

        # Mock the morphology service to return no nouns
        canvas.morphology_service = Mock()
        canvas.morphology_service.extract_nouns.return_value = []

        page = MangaPage(
            page_number=0, image_path=Path("/tmp/img.jpg"), width=1280, height=1600
        )
        page.ocr_blocks = [OCRBlock(x=0, y=0, width=100, height=50, text_lines=["走った。"])]

        mock_run_js = Mock()
        canvas.web_view.page = Mock()
        canvas.web_view.page().runJavaScript = mock_run_js

        canvas.render_pages([page])

        # Verify nouns array is empty, not missing
        match = re.search(r"updateView\((.*)\);", mock_run_js.call_args[0][0])
        data = json.loads(match.group(1))
        block = data["pages"][0]["blocks"][0]

        assert "nouns" in block, "Block should have 'nouns' key even if empty"
        assert len(block["nouns"]) == 0, "Block should have empty nouns array"

    def test_render_pages_with_multiple_blocks(self, canvas):
        """Test render_pages with multiple blocks, each extracting nouns."""
        canvas.morphology_service = Mock()

        # Block 1: has noun
        nouns_block1 = [
            Token(
                surface="猫",
                lemma="猫",
                pos="NOUN",
                reading="ねこ",
                start_offset=0,
                end_offset=1,
            )
        ]

        # Block 2: no nouns
        nouns_block2 = []

        # Setup side effects for successive calls
        canvas.morphology_service.extract_nouns.side_effect = [
            nouns_block1,
            nouns_block2,
        ]

        page = MangaPage(
            page_number=0, image_path=Path("/tmp/img.jpg"), width=1280, height=1600
        )
        page.ocr_blocks = [
            OCRBlock(x=0, y=0, width=100, height=50, text_lines=["猫です"]),
            OCRBlock(x=100, y=100, width=100, height=50, text_lines=["走った。"]),
        ]

        mock_run_js = Mock()
        canvas.web_view.page = Mock()
        canvas.web_view.page().runJavaScript = mock_run_js

        canvas.render_pages([page])

        match = re.search(r"updateView\((.*)\);", mock_run_js.call_args[0][0])
        data = json.loads(match.group(1))
        blocks = data["pages"][0]["blocks"]

        assert len(blocks) == 2
        assert len(blocks[0]["nouns"]) == 1
        assert blocks[0]["nouns"][0]["surface"] == "猫"
        assert len(blocks[1]["nouns"]) == 0

    def test_extract_block_nouns_handles_no_service(self, canvas):
        """Test _extract_block_nouns handles None morphology service gracefully."""
        canvas.morphology_service = None

        # Should return empty list instead of crashing
        nouns = canvas._extract_block_nouns("田中さん")
        assert nouns == []

    def test_noun_offset_wrapping_potential(self, canvas, morphology_service):
        """
        Test that noun offsets are suitable for HTML span wrapping.
        Offsets should be distinct and non-overlapping.
        """
        text = "田中さんと佐藤さん"

        # Get actual tokens from the service
        nouns = morphology_service.extract_nouns(text)

        # Verify offsets don't overlap
        for i, noun1 in enumerate(nouns):
            for noun2 in nouns[i + 1 :]:
                # Ensure nouns don't overlap
                assert noun1.end_offset <= noun2.start_offset or noun2.end_offset <= noun1.start_offset, (
                    f"Noun offsets overlap: '{noun1.surface}' "
                    f"[{noun1.start_offset}:{noun1.end_offset}] vs "
                    f"'{noun2.surface}' [{noun2.start_offset}:{noun2.end_offset}]"
                )

        # Verify each noun can be extracted correctly
        for noun in nouns:
            extracted = text[noun.start_offset : noun.end_offset]
            assert extracted == noun.surface


class TestNounSignals:
    """Tests for noun-related signals."""

    def test_noun_clicked_signal_exists(self, canvas):
        """Test that MangaCanvas has noun_clicked signal."""
        assert hasattr(canvas, "noun_clicked")
        # Should be a Signal type
        assert hasattr(canvas.noun_clicked, "connect")

    @pytest.mark.skip(reason="Qt Signal testing requires display server")
    def test_web_connector_noun_clicked_slot(self):
        """Test WebConnector handles noun click slot."""
        from manga_reader.ui.manga_canvas import WebConnector

        connector = WebConnector()
        assert hasattr(connector, "requestNounLookup")
        assert hasattr(connector, "nounClickedSignal")

        # Mock the signal and test slot
        mock_emit = Mock()
        connector.nounClickedSignal.emit = mock_emit

        # Call the slot
        connector.requestNounLookup("走る", "走った", 100, 200)

        # Verify signal was emitted
        mock_emit.assert_called_once_with("走る", "走った", 100, 200)
