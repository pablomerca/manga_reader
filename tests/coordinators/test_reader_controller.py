"""Unit tests for ReaderController coordinator."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from PySide6.QtCore import QObject

from manga_reader.coordinators import ReaderController, WordInteractionCoordinator, ContextPanelCoordinator
from manga_reader.coordinators.view_modes import DOUBLE_PAGE_MODE, SINGLE_PAGE_MODE
from manga_reader.core import MangaPage, MangaVolume, OCRBlock, TrackedWord, WordAppearance
from manga_reader.io import DatabaseManager
from manga_reader.services import DictionaryService, MorphologyService, VocabularyService
from manga_reader.ui import MainWindow, MangaCanvas, WordContextPanel


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_main_window():
    """Mock MainWindow for testing."""
    window = MagicMock()
    window.show_info = MagicMock()
    window.show_error = MagicMock()
    return window


@pytest.fixture
def mock_canvas():
    """Mock MangaCanvas for testing."""
    canvas = MagicMock()
    canvas.render_pages = MagicMock()
    canvas.hide_dictionary_popup = MagicMock()
    canvas.show_dictionary_popup = MagicMock()
    return canvas


@pytest.fixture
def mock_ingestor():
    """Mock VolumeIngestor for testing."""
    ingestor = MagicMock()
    return ingestor


@pytest.fixture
def mock_dictionary_service():
    """Mock DictionaryService for testing."""
    service = MagicMock()
    return service


@pytest.fixture
def mock_vocabulary_service(tmp_path):
    """Create a real VocabularyService with in-memory database for testing."""
    db_path = tmp_path / "vocab.db"
    db = DatabaseManager(db_path)
    db.ensure_schema()
    
    # Use a fake morphology for deterministic testing
    class FakeMorphology:
        def tokenize(self, text: str):
            class T:
                def __init__(self):
                    self.lemma = text.lower()
                    self.reading = text
                    self.pos = "NOUN"
            return [T()] if text else []
    
    service = VocabularyService(db, FakeMorphology())
    return service


@pytest.fixture
def mock_context_panel():
    """Mock WordContextPanel for testing."""
    panel = MagicMock()
    panel.display_word_context = MagicMock()
    panel.clear = MagicMock()
    panel.closed = MagicMock()
    panel.appearance_selected = MagicMock()
    return panel


@pytest.fixture
def controller(mock_main_window, mock_canvas, mock_ingestor, 
               mock_dictionary_service, mock_vocabulary_service, mock_context_panel):
    """Create a ReaderController with mocked dependencies and coordinators."""
    word_coord = WordInteractionCoordinator(
        canvas=mock_canvas,
        dictionary_service=mock_dictionary_service,
        vocabulary_service=mock_vocabulary_service,
        main_window=mock_main_window,
    )
    context_coord = ContextPanelCoordinator(
        context_panel=mock_context_panel,
        vocabulary_service=mock_vocabulary_service,
        main_window=mock_main_window,
        word_interaction=word_coord,
    )
    ctrl = ReaderController(
        main_window=mock_main_window,
        canvas=mock_canvas,
        ingestor=mock_ingestor,
        word_interaction=word_coord,
        context_coordinator=context_coord,
    )
    return ctrl


@pytest.fixture
def sample_volume(tmp_path):
    """Create a sample manga volume for testing."""
    volume_path = tmp_path / "test_volume"
    volume_path.mkdir()
    
    # Create sample pages
    pages = [
        MangaPage(
            page_number=0,
            image_path=volume_path / "0001.jpg",
            width=1280,
            height=1600,
            ocr_blocks=[
                OCRBlock(x=100, y=200, width=300, height=50, text_lines=["test text"])
            ]
        ),
        MangaPage(
            page_number=1,
            image_path=volume_path / "0002.jpg",
            width=1280,
            height=1600,
            ocr_blocks=[
                OCRBlock(x=150, y=250, width=300, height=50, text_lines=["more test text"])
            ]
        ),
    ]
    
    volume = MangaVolume(title="Test Volume", volume_path=volume_path, pages=pages)
    return volume


# ============================================================================
# Tests for handle_volume_opened
# ============================================================================


class TestHandleVolumeOpened:
    """Tests for the handle_volume_opened slot."""

    def test_volume_loaded_successfully(self, controller, mock_ingestor, 
                                        mock_canvas, mock_main_window, sample_volume):
        """Test successful volume loading."""
        volume_path = sample_volume.volume_path
        mock_ingestor.ingest_volume.return_value = sample_volume
        
        controller.handle_volume_opened(volume_path)
        
        assert controller.current_volume == sample_volume
        assert controller.current_page_number == 0
        mock_canvas.render_pages.assert_called_once()
        mock_main_window.show_info.assert_called_once()

    def test_volume_load_failure(self, controller, mock_ingestor, 
                                 mock_main_window):
        """Test failure when ingestor returns None."""
        volume_path = Path("/nonexistent")
        mock_ingestor.ingest_volume.return_value = None
        
        controller.handle_volume_opened(volume_path)
        
        assert controller.current_volume is None
        mock_main_window.show_error.assert_called_once()

    def test_empty_volume_rejected(self, controller, mock_ingestor, 
                                    mock_main_window):
        """Test rejection of volume with no pages."""
        volume_path = Path("/test")
        empty_volume = MangaVolume(title="Empty", volume_path=volume_path, pages=[])
        mock_ingestor.ingest_volume.return_value = empty_volume
        
        controller.handle_volume_opened(volume_path)
        
        assert controller.current_volume is None
        mock_main_window.show_error.assert_called_once()


# ============================================================================
# Tests for handle_word_clicked
# ============================================================================


class TestHandleWordClicked:
    """Tests for the handle_word_clicked slot."""

    def test_word_clicked_with_dictionary_entry(self, controller, 
                                                 mock_canvas, mock_dictionary_service):
        """Test word click when dictionary has an entry."""
        mock_entry = MagicMock()
        mock_entry.reading = "てすと"
        mock_entry.senses = [
            MagicMock(glosses=["test"], pos="Noun")
        ]
        mock_dictionary_service.lookup.return_value = mock_entry
        
        controller.handle_word_clicked("test", "test", 100, 200)
        
        mock_canvas.show_dictionary_popup.assert_called_once()
        payload = mock_canvas.show_dictionary_popup.call_args[0][0]
        assert payload["surface"] == "test"
        assert payload["reading"] == "てすと"
        assert not payload["notFound"]

    def test_word_clicked_without_dictionary_entry(self, controller,
                                                     mock_canvas, mock_dictionary_service):
        """Test word click when word is not in dictionary."""
        mock_dictionary_service.lookup.return_value = None
        
        controller.handle_word_clicked("unknown", "unknown", 100, 200)
        
        mock_canvas.show_dictionary_popup.assert_called_once()
        payload = mock_canvas.show_dictionary_popup.call_args[0][0]
        assert payload["notFound"] is True
        assert payload["reading"] == ""
        assert payload["senses"] == []


# ============================================================================
# Tests for handle_track_word
# ============================================================================


class TestHandleTrackWord:
    """Tests for the handle_track_word slot."""

    def test_track_word_without_open_volume(self, controller, mock_main_window):
        """Test tracking a word when no volume is open."""
        assert controller.current_volume is None
        
        controller.handle_track_word("taberu", "たべる", "Verb")
        
        mock_main_window.show_error.assert_called_once()

    def test_track_word_successfully(self, controller, sample_volume, 
                                      mock_main_window):
        """Test successfully tracking a word with an open volume."""
        controller.current_volume = sample_volume
        controller.current_page_number = 0
        
        controller.handle_track_word("taberu", "たべる", "Verb")
        
        mock_main_window.show_info.assert_called_once()
        tracked_words = controller.word_interaction.vocabulary_service.list_tracked_words()
        assert len(tracked_words) == 1
        assert tracked_words[0].lemma == "taberu"

    def test_track_word_error_handling(self, controller, sample_volume,
                                        mock_main_window):
        """Test error handling when tracking fails."""
        controller.current_volume = sample_volume
        controller.current_page_number = 0
        
        # Mock the vocabulary service to raise an exception
        controller.word_interaction.vocabulary_service.track_word = MagicMock(
            side_effect=Exception("Database error")
        )
        
        controller.handle_track_word("taberu", "たべる", "Verb")
        
        mock_main_window.show_error.assert_called_once()


# ============================================================================
# Tests for handle_view_word_context
# ============================================================================


class TestHandleViewWordContext:
    """Tests for the handle_view_word_context slot."""

    def test_view_context_with_appearances(self, controller, 
                                            mock_vocabulary_service, mock_main_window,
                                            mock_context_panel, tmp_path):
        """Test viewing context for a tracked word with multiple appearances."""
        # Setup: create a tracked word with multiple appearances
        word = mock_vocabulary_service._db.upsert_tracked_word("taberu", "たべる", "Verb")
        vol1 = mock_vocabulary_service._db.upsert_volume(tmp_path / "vol1", "Volume 1")
        vol2 = mock_vocabulary_service._db.upsert_volume(tmp_path / "vol2", "Volume 2")
        
        # Add multiple appearances
        mock_vocabulary_service._db.insert_word_appearance(
            word.id, vol1.id, 0, {"x": 0, "y": 0}, "sentence 1"
        )
        mock_vocabulary_service._db.insert_word_appearance(
            word.id, vol2.id, 5, {"x": 100, "y": 100}, "sentence 2"
        )
        
        controller.handle_view_word_context(word.id)
        
        # Verify the context panel was shown with data
        mock_context_panel.display_word_context.assert_called_once()
        call_args = mock_context_panel.display_word_context.call_args
        assert call_args[1]["word_id"] == word.id
        assert call_args[1]["word_lemma"] == "taberu"
        assert len(call_args[1]["appearances"]) == 2
        
        # Verify main window shows the panel
        mock_main_window.show_context_panel.assert_called_once()

    def test_view_context_no_appearances(self, controller, 
                                          mock_vocabulary_service, mock_main_window, tmp_path):
        """Test viewing context for a word with no recorded appearances."""
        word = mock_vocabulary_service._db.upsert_tracked_word("orphan", "もじ", "Noun")
        
        controller.handle_view_word_context(word.id)
        
        mock_main_window.show_info.assert_called_once()
        call_args = mock_main_window.show_info.call_args
        assert "No Appearances" in call_args[0][0]

    def test_view_context_truncates_long_sentence(self, controller,
                                                   mock_vocabulary_service, mock_main_window,
                                                   mock_context_panel, tmp_path):
        """Test that long sentences are displayed in the context panel."""
        word = mock_vocabulary_service._db.upsert_tracked_word("test", "てすと", "Noun")
        vol = mock_vocabulary_service._db.upsert_volume(tmp_path / "vol", "Test")
        
        long_sentence = "x" * 100  # 100 character sentence
        mock_vocabulary_service._db.insert_word_appearance(
            word.id, vol.id, 0, {"x": 0, "y": 0}, long_sentence
        )
        
        controller.handle_view_word_context(word.id)
        
        # Verify context panel was called with the appearance
        mock_context_panel.display_word_context.assert_called_once()
        call_args = mock_context_panel.display_word_context.call_args
        appearances = call_args[1]["appearances"]
        assert len(appearances) == 1
        # The context panel will handle truncation in its display method

    def test_view_context_handles_more_than_five(self, controller,
                                                   mock_vocabulary_service, mock_main_window,
                                                   mock_context_panel, tmp_path):
        """Test that all occurrences are passed to the context panel."""
        word = mock_vocabulary_service._db.upsert_tracked_word("many", "おおい", "Adjective")
        vol = mock_vocabulary_service._db.upsert_volume(tmp_path / "vol", "Test")
        
        # Add 7 appearances
        for i in range(7):
            mock_vocabulary_service._db.insert_word_appearance(
                word.id, vol.id, i, {"x": 0, "y": 0}, f"sentence {i}"
            )
        
        controller.handle_view_word_context(word.id)
        
        # Verify all 7 appearances are passed to the panel
        mock_context_panel.display_word_context.assert_called_once()
        call_args = mock_context_panel.display_word_context.call_args
        appearances = call_args[1]["appearances"]
        assert len(appearances) == 7

    def test_view_context_error_handling(self, controller, mock_main_window):
        """Test error handling when context lookup fails."""
        # Mock the vocabulary service to raise an exception
        controller.context_coordinator.vocabulary_service.list_appearances = MagicMock(
            side_effect=Exception("Database error")
        )
        
        controller.handle_view_word_context(999)
        
        mock_main_window.show_error.assert_called_once()


# ============================================================================
# Tests for handle_open_vocabulary_list
# ============================================================================


class TestHandleOpenVocabularyList:
    """Tests for the handle_open_vocabulary_list slot."""

    def test_empty_vocabulary_list(self, controller, mock_main_window, sample_volume):
        """Test showing empty vocabulary list."""
        controller.handle_open_vocabulary_list()
        
        mock_main_window.show_info.assert_called_once()
        call_args = mock_main_window.show_info.call_args
        assert "haven't tracked any words" in call_args[0][1].lower()

    def test_vocabulary_list_with_words(self, controller, mock_main_window,
                                         mock_vocabulary_service, sample_volume, tmp_path):
        """Test showing vocabulary list with tracked words."""
        # Add some tracked words
        mock_vocabulary_service.track_word(
            lemma="taberu", reading="たべる", part_of_speech="Verb",
            volume_path=sample_volume.volume_path, page_index=0,
            crop_coordinates={"x": 0, "y": 0}, sentence_text="test"
        )
        mock_vocabulary_service.track_word(
            lemma="hashiru", reading="はしる", part_of_speech="Verb",
            volume_path=sample_volume.volume_path, page_index=1,
            crop_coordinates={"x": 0, "y": 0}, sentence_text="test"
        )
        
        controller.handle_open_vocabulary_list()
        
        mock_main_window.show_info.assert_called_once()
        call_args = mock_main_window.show_info.call_args
        message = call_args[0][1]
        assert "2 word(s)" in message
        assert "taberu" in message
        assert "hashiru" in message

    def test_vocabulary_list_truncates_long_lists(self, controller, mock_main_window,
                                                   mock_vocabulary_service, sample_volume):
        """Test that lists with >10 words show '... and more'."""
        # Add 15 tracked words
        for i in range(15):
            mock_vocabulary_service.track_word(
                lemma=f"word{i}", reading=f"word{i}", part_of_speech="Noun",
                volume_path=sample_volume.volume_path, page_index=0,
                crop_coordinates={"x": 0, "y": 0}, sentence_text="test"
            )
        
        controller.handle_open_vocabulary_list()
        
        call_args = mock_main_window.show_info.call_args
        message = call_args[0][1]
        assert "15 word(s)" in message
        assert "... and 5 more" in message

    def test_vocabulary_list_error_handling(self, controller, mock_main_window):
        """Test error handling when listing vocabulary fails."""
        controller.context_coordinator.vocabulary_service.list_tracked_words = MagicMock(
            side_effect=Exception("Database error")
        )
        
        controller.handle_open_vocabulary_list()
        
        mock_main_window.show_error.assert_called_once()


# ============================================================================
# Tests for navigation
# ============================================================================


class TestNavigation:
    """Tests for page navigation methods."""

    def test_next_page_single_mode(self, controller, sample_volume):
        """Test next page navigation in single page mode."""
        controller.current_volume = sample_volume
        controller.current_page_number = 0
        controller.view_mode = SINGLE_PAGE_MODE
        
        controller.next_page()
        
        assert controller.current_page_number == 1

    def test_next_page_at_end(self, controller, sample_volume):
        """Test next page when already at last page."""
        controller.current_volume = sample_volume
        controller.current_page_number = 1  # Last page (0-indexed)
        
        controller.next_page()
        
        # Should remain at last page
        assert controller.current_page_number == 1

    def test_previous_page(self, controller, sample_volume):
        """Test previous page navigation."""
        controller.current_volume = sample_volume
        controller.current_page_number = 1
        
        controller.previous_page()
        
        assert controller.current_page_number == 0

    def test_previous_page_at_start(self, controller, sample_volume):
        """Test previous page when already at first page."""
        controller.current_volume = sample_volume
        controller.current_page_number = 0
        
        controller.previous_page()
        
        # Should remain at first page
        assert controller.current_page_number == 0

    def test_jump_to_page_valid(self, controller, sample_volume):
        """Test jumping to a valid page."""
        controller.current_volume = sample_volume
        
        controller.jump_to_page(1)
        
        assert controller.current_page_number == 1

    def test_jump_to_page_invalid(self, controller, sample_volume):
        """Test jumping to an invalid page."""
        controller.current_volume = sample_volume
        controller.current_page_number = 0
        
        controller.jump_to_page(99)
        
        # Should remain unchanged
        assert controller.current_page_number == 0


# ============================================================================
# Tests for view mode
# ============================================================================


class TestViewMode:
    """Tests for view mode changes."""

    def test_change_to_double_mode(self, controller, sample_volume, mock_canvas):
        """Test changing to double page mode."""
        controller.current_volume = sample_volume
        controller.view_mode = SINGLE_PAGE_MODE
        
        controller.handle_view_mode_changed("double")
        
        assert controller.view_mode.name == "double"
        mock_canvas.render_pages.assert_called()

    def test_change_to_single_mode(self, controller, sample_volume, mock_canvas):
        """Test changing to single page mode."""
        controller.current_volume = sample_volume
        controller.view_mode = DOUBLE_PAGE_MODE
        
        controller.handle_view_mode_changed("single")
        
        assert controller.view_mode.name == "single"
        mock_canvas.render_pages.assert_called()

    def test_invalid_view_mode_raises(self, controller, sample_volume):
        """Test that invalid view modes raise a ValueError (fail-fast)."""
        controller.view_mode = SINGLE_PAGE_MODE

        import pytest as _pytest
        with _pytest.raises(ValueError):
            controller.handle_view_mode_changed("invalid")

        # State remains unchanged after exception
        assert controller.view_mode.name == "single"
