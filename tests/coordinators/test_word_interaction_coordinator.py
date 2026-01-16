"""Unit tests for WordInteractionCoordinator."""

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from manga_reader.coordinators import WordInteractionCoordinator
from manga_reader.core import MangaPage, MangaVolume, OCRBlock


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_canvas():
    """Mock MangaCanvas for testing."""
    canvas = MagicMock()
    canvas.show_dictionary_popup = MagicMock()
    return canvas


@pytest.fixture
def mock_dictionary_service():
    """Mock DictionaryService for testing."""
    service = MagicMock()
    return service


@pytest.fixture
def mock_vocabulary_service():
    """Mock VocabularyService for testing."""
    service = MagicMock()
    return service


@pytest.fixture
def mock_main_window():
    """Mock MainWindow for testing."""
    window = MagicMock()
    window.show_info = MagicMock()
    window.show_error = MagicMock()
    return window


@pytest.fixture
def coordinator(mock_canvas, mock_dictionary_service, mock_vocabulary_service, mock_main_window):
    """Create a WordInteractionCoordinator with mocked dependencies."""
    return WordInteractionCoordinator(
        canvas=mock_canvas,
        dictionary_service=mock_dictionary_service,
        vocabulary_service=mock_vocabulary_service,
        main_window=mock_main_window,
    )


@pytest.fixture
def sample_volume(tmp_path):
    """Create a sample volume with OCR blocks."""
    volume_path = tmp_path / "test_volume"
    volume_path.mkdir()
    
    pages = [
        MangaPage(
            page_number=0,
            image_path=volume_path / "0001.jpg",
            width=1280,
            height=1600,
            ocr_blocks=[
                OCRBlock(x=100, y=200, width=300, height=50, text_lines=["This is test text"]),
                OCRBlock(x=100, y=300, width=300, height=50, text_lines=["Another line with words"]),
            ]
        ),
    ]
    
    return MangaVolume(title="Test Volume", volume_path=volume_path, pages=pages)


# ============================================================================
# Tests for handle_word_clicked
# ============================================================================


class TestHandleWordClicked:
    """Tests for word click handling."""

    def test_word_clicked_shows_popup(self, coordinator, mock_canvas, mock_dictionary_service):
        """Test that word click shows dictionary popup."""
        # Setup dictionary entry
        mock_entry = MagicMock()
        mock_entry.reading = "よむ"
        mock_entry.senses = [MagicMock(glosses=["to read"], pos="Verb")]
        mock_dictionary_service.lookup.return_value = mock_entry
        
        # Click a word
        coordinator.handle_word_clicked("読む", "読んで", 100, 200)
        
        # Assert popup was shown
        mock_canvas.show_dictionary_popup.assert_called_once()
        payload = mock_canvas.show_dictionary_popup.call_args[0][0]
        assert payload["lemma"] == "読む"
        # Surface is normalized to lemma for display, original surface preserved in surfaceOriginal
        assert payload["surface"] == "読む"
        assert payload["surfaceOriginal"] == "読んで"
        assert payload["reading"] == "よむ"
        assert not payload["notFound"]

    def test_word_not_in_dictionary(self, coordinator, mock_canvas, mock_dictionary_service):
        """Test handling when word is not found in dictionary."""
        mock_dictionary_service.lookup.return_value = None
        
        coordinator.handle_word_clicked("unknown", "unknown", 100, 200)
        
        mock_canvas.show_dictionary_popup.assert_called_once()
        payload = mock_canvas.show_dictionary_popup.call_args[0][0]
        assert payload["notFound"] is True
        assert payload["reading"] == ""
        assert payload["senses"] == []

    def test_word_click_with_block_context(self, coordinator, mock_canvas, mock_dictionary_service, 
                                            mock_vocabulary_service, sample_volume):
        """Test that sentence context is captured from OCR block."""
        coordinator.set_volume_context(sample_volume, 0)
        
        mock_entry = MagicMock()
        mock_entry.reading = "テスト"
        mock_entry.senses = []
        mock_dictionary_service.lookup.return_value = mock_entry
        mock_vocabulary_service.is_word_tracked.return_value = False
        
        # Click word in first block
        coordinator.handle_word_clicked("test", "test", 150, 220, page_index=0, block_id=0)
        
        # Verify context was stored
        assert coordinator.last_clicked_block_text == "This is test text"

    def test_tracked_word_shows_in_popup(self, coordinator, mock_canvas, mock_dictionary_service,
                                         mock_vocabulary_service):
        """Test that tracked status appears in dictionary popup."""
        mock_entry = MagicMock()
        mock_entry.reading = "てすと"
        mock_entry.senses = []
        mock_dictionary_service.lookup.return_value = mock_entry
        mock_vocabulary_service.is_word_tracked.return_value = True
        
        coordinator.handle_word_clicked("test", "test", 100, 200)
        
        payload = mock_canvas.show_dictionary_popup.call_args[0][0]
        assert payload["isTracked"] is True


# ============================================================================
# Tests for handle_track_word
# ============================================================================


class TestHandleTrackWord:
    """Tests for word tracking."""

    def test_track_word_without_volume(self, coordinator, mock_main_window):
        """Test that tracking without open volume raises error."""
        import pytest
        with pytest.raises(RuntimeError):
            coordinator.handle_track_word("test", "てすと", "Noun")

    def test_track_word_successfully(self, coordinator, mock_vocabulary_service, mock_main_window, sample_volume):
        """Test successfully tracking a word."""
        coordinator.set_volume_context(sample_volume, 0)
        coordinator.last_clicked_block_text = "test sentence"
        coordinator.last_clicked_crop_coords = {"x": 100, "y": 200, "width": 300, "height": 50}
        
        coordinator.handle_track_word("taberu", "たべる", "Verb")
        
        mock_vocabulary_service.track_word.assert_called_once()
        args = mock_vocabulary_service.track_word.call_args[1]
        assert args["lemma"] == "taberu"
        assert args["reading"] == "たべる"
        assert args["part_of_speech"] == "Verb"
        assert args["page_index"] == 0
        
        mock_main_window.show_info.assert_called_once()

    def test_track_word_with_sentence_context(self, coordinator, mock_vocabulary_service, sample_volume):
        """Test that sentence context is used when tracking."""
        coordinator.set_volume_context(sample_volume, 0)
        coordinator.last_clicked_block_text = "Custom sentence with the word"
        coordinator.last_clicked_crop_coords = {"x": 100, "y": 200, "width": 300, "height": 50}
        
        coordinator.handle_track_word("word", "ワード", "Noun")
        
        args = mock_vocabulary_service.track_word.call_args[1]
        assert args["sentence_text"] == "Custom sentence with the word"

    def test_track_word_error_handling(self, coordinator, mock_vocabulary_service, mock_main_window, sample_volume):
        """Test error handling when tracking fails."""
        coordinator.set_volume_context(sample_volume, 0)
        coordinator.last_clicked_block_text = "test sentence"
        coordinator.last_clicked_crop_coords = {"x": 100, "y": 200, "width": 300, "height": 50}
        mock_vocabulary_service.track_word.side_effect = Exception("DB error")
        
        coordinator.handle_track_word("test", "てすと", "Noun")
        
        mock_main_window.show_error.assert_called_once()

    def test_track_word_uses_correct_page_context(self, coordinator, mock_vocabulary_service, sample_volume):
        """Test that track_word uses the page where word was clicked."""
        coordinator.set_volume_context(sample_volume, 0)
        coordinator.last_clicked_page_index = 0  # Set from word click
        coordinator.last_clicked_block_text = "test sentence"
        coordinator.last_clicked_crop_coords = {"x": 100, "y": 200, "width": 300, "height": 50}
        
        coordinator.handle_track_word("test", "てすと", "Noun")
        
        args = mock_vocabulary_service.track_word.call_args[1]
        assert args["page_index"] == 0


# ============================================================================
# Tests for volume context management
# ============================================================================


class TestVolumeContext:
    """Tests for volume context management."""

    def test_set_volume_context(self, coordinator, sample_volume):
        """Test setting volume context."""
        coordinator.set_volume_context(sample_volume, 0)
        
        assert coordinator._current_volume == sample_volume
        assert coordinator._current_page == 0

    def test_volume_context_used_in_block_lookup(self, coordinator, mock_canvas, 
                                                  mock_dictionary_service, sample_volume):
        """Test that volume context is used to find block text."""
        coordinator.set_volume_context(sample_volume, 0)
        mock_entry = MagicMock()
        mock_entry.reading = "テスト"
        mock_entry.senses = []
        mock_dictionary_service.lookup.return_value = mock_entry
        
        # Click word in first OCR block at specific coordinates
        coordinator.handle_word_clicked("test", "test", 150, 220, page_index=-1, block_id=-1)
        
        # Block should be found and text stored
        assert coordinator.last_clicked_block_text is not None

    def test_page_fallback_when_no_explicit_page(self, coordinator, sample_volume):
        """Test that current page is used when no page_index provided."""
        coordinator.set_volume_context(sample_volume, 0)
        coordinator.handle_word_clicked("test", "test", 100, 200, page_index=-1)
        
        assert coordinator.last_clicked_page_index == 0
