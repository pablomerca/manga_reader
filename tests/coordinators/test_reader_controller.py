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
    window.show_sentence_panel = MagicMock()
    window.hide_sentence_panel = MagicMock()
    return window


@pytest.fixture
def mock_canvas():
    """Mock MangaCanvas for testing."""
    class DummySignal:
        def __init__(self):
            self._slots = []
        def connect(self, slot):
            self._slots.append(slot)
        def emit(self, *args, **kwargs):
            for slot in self._slots:
                slot(*args, **kwargs)

    canvas = MagicMock()
    canvas.render_pages = MagicMock()
    canvas.hide_dictionary_popup = MagicMock()
    canvas.show_dictionary_popup = MagicMock()
    canvas.block_clicked = DummySignal()
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
    class DummySignal:
        def __init__(self):
            self._slots = []
        def connect(self, slot):
            self._slots.append(slot)
        def emit(self, *args, **kwargs):
            for slot in self._slots:
                slot(*args, **kwargs)
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
    context_sync_coord = MagicMock()
    mock_library_coordinator = MagicMock()
    sentence_panel = MagicMock()
    sentence_panel.translate_clicked = DummySignal()
    sentence_panel.explain_clicked = DummySignal()
    sentence_panel.close_clicked = DummySignal()
    sentence_panel.set_original_text = MagicMock()
    sentence_panel.clear = MagicMock()
    sentence_panel.show = MagicMock()
    sentence_panel.hide = MagicMock()

    sentence_analysis_coord = MagicMock()
    sentence_analysis_coord.on_block_selected = MagicMock()
    sentence_analysis_coord.on_panel_closed = MagicMock()
    sentence_analysis_coord.request_translation = MagicMock()
    sentence_analysis_coord.request_explanation = MagicMock()

    ctrl = ReaderController(
        main_window=mock_main_window,
        canvas=mock_canvas,
        ingestor=mock_ingestor,
        word_interaction=word_coord,
        context_coordinator=context_coord,
        context_sync_coordinator=context_sync_coord,
        vocabulary_service=mock_vocabulary_service,
        library_coordinator=mock_library_coordinator,
        sentence_analysis_coordinator=sentence_analysis_coord,
        sentence_analysis_panel=sentence_panel,
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


def test_handle_block_clicked_opens_sentence_panel(controller, sample_volume):
    """Block clicks should open the sentence analysis panel with block text."""
    controller.current_volume = sample_volume
    controller.current_page_number = 0

    controller._handle_block_clicked(block_id=0, page_index=0)

    controller.sentence_panel.set_original_text.assert_called_once_with("test text")
    controller.main_window.show_sentence_panel.assert_called_once()
    controller.sentence_analysis_coordinator.on_block_selected.assert_called_once()


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
        
        # Setup library coordinator mock to return a library_volume with id
        library_volume_mock = MagicMock()
        library_volume_mock.id = 1
        library_volume_mock.last_page_read = 0
        controller.library_coordinator.add_volume_to_library.return_value = library_volume_mock
        
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
        """Test tracking a word when no volume is open raises RuntimeError."""
        assert controller.current_volume is None
        
        import pytest as _pytest
        with _pytest.raises(RuntimeError):
            controller.handle_track_word("taberu", "たべる", "Verb")

    def test_track_word_successfully(self, controller, sample_volume, 
                                      mock_main_window):
        """Test successfully tracking a word with an open volume."""
        controller.current_volume = sample_volume
        controller.current_page_number = 0
        # Set volume context in word interaction coordinator
        controller.word_interaction.set_volume_context(sample_volume, 0)
        controller.word_interaction.last_clicked_block_text = "test sentence"
        controller.word_interaction.last_clicked_crop_coords = {"x": 100, "y": 200, "width": 300, "height": 50}
        
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
        controller.word_interaction.set_volume_context(sample_volume, 0)
        controller.word_interaction.last_clicked_block_text = "test sentence"
        controller.word_interaction.last_clicked_crop_coords = {"x": 100, "y": 200, "width": 300, "height": 50}
        
        # Mock the vocabulary service to raise an exception
        controller.word_interaction.vocabulary_service.track_word = MagicMock(
            side_effect=Exception("Database error")
        )
        
        controller.handle_track_word("taberu", "たべる", "Verb")
        
        # Verify error was shown to user
        mock_main_window.show_error.assert_called_once()
        call_args = mock_main_window.show_error.call_args
        assert "Tracking Failed" in call_args[0][0]


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

    def test_toggle_view_mode_single_to_double(self, controller, sample_volume, mock_canvas):
        """Test toggling from single to double page mode."""
        controller.current_volume = sample_volume
        controller.view_mode = SINGLE_PAGE_MODE
        
        controller.toggle_view_mode()
        
        assert controller.view_mode.name == "double"
        mock_canvas.render_pages.assert_called()

    def test_toggle_view_mode_double_to_single(self, controller, sample_volume, mock_canvas):
        """Test toggling from double to single page mode."""
        controller.current_volume = sample_volume
        controller.view_mode = DOUBLE_PAGE_MODE
        
        controller.toggle_view_mode()
        
        assert controller.view_mode.name == "single"
        mock_canvas.render_pages.assert_called()

    def test_toggle_view_mode_emits_signal_single_to_double(self, controller, sample_volume):
        """Test that toggle emits view_mode_updated signal with correct mode."""
        from unittest.mock import MagicMock
        controller.current_volume = sample_volume
        controller.view_mode = SINGLE_PAGE_MODE
        
        # Connect to the signal
        signal_spy = MagicMock()
        controller.view_mode_updated.connect(signal_spy)
        
        controller.toggle_view_mode()
        
        # Verify signal was emitted with the new mode name
        signal_spy.assert_called_once_with("double")

    def test_toggle_view_mode_emits_signal_double_to_single(self, controller, sample_volume):
        """Test that toggle emits view_mode_updated signal with correct mode."""
        from unittest.mock import MagicMock
        controller.current_volume = sample_volume
        controller.view_mode = DOUBLE_PAGE_MODE
        
        # Connect to the signal
        signal_spy = MagicMock()
        controller.view_mode_updated.connect(signal_spy)
        
        controller.toggle_view_mode()
        
        # Verify signal was emitted with the new mode name
        signal_spy.assert_called_once_with("single")


# =========================================================================
# Tests for context synchronization wiring
# =========================================================================


def test_handle_sync_context_requests_run_sync(controller):
    """Ensure sync request delegates to the context sync coordinator."""
    # context_sync_coordinator is a MagicMock added in the controller fixture
    controller.context_sync_coordinator.synchronize_current_volume = MagicMock()

    controller.handle_sync_context_requested()

    controller.context_sync_coordinator.synchronize_current_volume.assert_called_once()


# ============================================================================
# Tests for block highlighting (Phase 4)
# ============================================================================


def test_handle_navigate_to_appearance_jumps_to_page(controller, sample_volume):
    """Test that navigating to appearance jumps to correct page."""
    sample_volume.volume_id = 1  # Set volume_id to match the one being navigated to
    controller.current_volume = sample_volume
    controller.current_page_number = 0
    
    # Navigate to appearance on page 1
    crop_coords = {'x': 100, 'y': 200, 'width': 300, 'height': 50}
    controller.handle_navigate_to_appearance(volume_id=1, volume_path=str(sample_volume.volume_path), page_index=1, crop_coords=crop_coords)
    
    # Should have jumped to page 1
    assert controller.current_page_number == 1
    # Canvas should have been rendered
    controller.canvas.render_pages.assert_called()


def test_handle_navigate_to_appearance_highlights_block(controller, sample_volume):
    """Test that highlight method is called with coordinates after navigation."""
    sample_volume.volume_id = 1  # Set volume_id to match the one being navigated to
    controller.current_volume = sample_volume
    controller.current_page_number = 0
    controller.canvas.highlight_block_at_coordinates = MagicMock()
    
    # Navigate to appearance
    crop_coords = {'x': 100, 'y': 200, 'width': 300, 'height': 50}
    controller.handle_navigate_to_appearance(volume_id=1, volume_path=str(sample_volume.volume_path), page_index=1, crop_coords=crop_coords)
    
    # Start the timer event loop to trigger the delayed highlight
    # (In real usage, the Qt event loop handles this; for testing we manually call it)
    if controller._highlight_timer:
        controller._highlight_timer.timeout.emit()
    
    # Highlight should be called with the coordinates
    controller.canvas.highlight_block_at_coordinates.assert_called_with(crop_coords)


def test_handle_navigate_to_appearance_no_volume(controller, sample_volume):
    """Test navigation when no volume is currently loaded, but volume exists in library."""
    # No current volume loaded
    controller.current_volume = None
    controller.canvas.highlight_block_at_coordinates = MagicMock()
    
    # Setup library repository to return the sample volume when queried
    sample_volume.volume_id = 1
    library_volume = MagicMock()
    library_volume.folder_path = sample_volume.volume_path
    library_volume.id = 1
    
    controller.library_coordinator.library_repository.get_volume_by_id.return_value = library_volume
    controller.library_coordinator.add_volume_to_library.return_value = library_volume
    controller.ingestor.ingest_volume.return_value = sample_volume
    
    crop_coords = {'x': 100, 'y': 200, 'width': 300, 'height': 50}
    controller.handle_navigate_to_appearance(volume_id=1, volume_path=str(sample_volume.volume_path), page_index=1, crop_coords=crop_coords)
    
    # Should have loaded the volume
    assert controller.current_volume == sample_volume
    # Should have jumped to page 1
    assert controller.current_page_number == 1
    # Highlight should eventually be called (via timer)
    if controller._highlight_timer:
        controller._highlight_timer.timeout.emit()
    controller.canvas.highlight_block_at_coordinates.assert_called_with(crop_coords)


def test_handle_navigate_to_appearance_different_volume(controller, sample_volume):
    """Test navigation to appearance in a DIFFERENT volume (bug fix test)."""
    # Setup: Current volume is volume 1
    sample_volume.volume_id = 1
    controller.current_volume = sample_volume
    controller.current_page_number = 0
    
    # Create a different volume (volume 2) to navigate to
    from pathlib import Path
    from manga_reader.core import MangaPage, OCRBlock
    
    other_volume = MangaVolume(
        title="Other Volume",
        volume_path=Path("/tmp/other_volume"),
        pages=[
            MangaPage(
                page_number=0,
                image_path=Path("/tmp/other_volume/0001.jpg"),
                width=1280,
                height=1600,
                ocr_blocks=[
                    OCRBlock(x=50, y=100, width=200, height=40, text_lines=["text"])
                ]
            ),
            MangaPage(
                page_number=1,
                image_path=Path("/tmp/other_volume/0002.jpg"),
                width=1280,
                height=1600,
                ocr_blocks=[
                    OCRBlock(x=60, y=120, width=250, height=45, text_lines=["text"])
                ]
            ),
        ],
        volume_id=2  # Different volume ID
    )
    
    # Setup mocks
    library_volume = MagicMock()
    library_volume.folder_path = other_volume.volume_path
    library_volume.id = 2
    
    controller.library_coordinator.library_repository.get_volume_by_id.return_value = library_volume
    controller.library_coordinator.add_volume_to_library.return_value = library_volume
    controller.ingestor.ingest_volume.return_value = other_volume
    controller.canvas.highlight_block_at_coordinates = MagicMock()
    
    # Navigate to appearance in volume 2
    crop_coords = {'x': 60, 'y': 120, 'width': 250, 'height': 45}
    controller.handle_navigate_to_appearance(volume_id=2, volume_path=str(other_volume.volume_path), page_index=1, crop_coords=crop_coords)
    
    # Should have SWITCHED to the different volume
    assert controller.current_volume == other_volume
    assert controller.current_volume.volume_id == 2
    # Should have jumped to page 1
    assert controller.current_page_number == 1
    # Highlight should eventually be called
    if controller._highlight_timer:
        controller._highlight_timer.timeout.emit()
    controller.canvas.highlight_block_at_coordinates.assert_called_with(crop_coords)
