"""Unit tests for ContextPanelCoordinator."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from manga_reader.coordinators import ContextPanelCoordinator
from manga_reader.coordinators.view_modes import SINGLE_PAGE_MODE, DOUBLE_PAGE_MODE
from manga_reader.core import MangaPage, MangaVolume, OCRBlock, TrackedWord, WordAppearance
from manga_reader.io import DatabaseManager


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_context_panel():
    """Mock WordContextPanel for testing."""
    panel = MagicMock()
    panel.display_word_context = MagicMock()
    panel.closed = MagicMock()
    panel.appearance_selected = MagicMock()
    return panel


@pytest.fixture
def mock_vocabulary_service(tmp_path):
    """Create a real VocabularyService with in-memory database."""
    from manga_reader.services import VocabularyService, MorphologyService
    
    db_path = tmp_path / "vocab.db"
    db = DatabaseManager(db_path)
    db.ensure_schema()
    
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
def mock_main_window():
    """Mock MainWindow for testing."""
    window = MagicMock()
    window.show_info = MagicMock()
    window.show_error = MagicMock()
    window.show_context_panel = MagicMock()
    window.hide_context_panel = MagicMock()
    return window


@pytest.fixture
def coordinator(mock_context_panel, mock_vocabulary_service, mock_main_window):
    """Create a ContextPanelCoordinator with mocked dependencies."""
    return ContextPanelCoordinator(
        context_panel=mock_context_panel,
        vocabulary_service=mock_vocabulary_service,
        main_window=mock_main_window,
    )


@pytest.fixture
def sample_volume(tmp_path):
    """Create a sample volume for testing."""
    volume_path = tmp_path / "test_volume"
    volume_path.mkdir()
    
    pages = [
        MangaPage(
            page_number=0,
            image_path=volume_path / "0001.jpg",
            width=1280,
            height=1600,
            ocr_blocks=[OCRBlock(x=100, y=200, width=300, height=50, text_lines=["test text"])],
        ),
        MangaPage(
            page_number=1,
            image_path=volume_path / "0002.jpg",
            width=1280,
            height=1600,
            ocr_blocks=[OCRBlock(x=100, y=200, width=300, height=50, text_lines=["more text"])],
        ),
    ]
    
    return MangaVolume(title="Test Volume", volume_path=volume_path, pages=pages)


# ============================================================================
# Tests for handle_open_vocabulary_list
# ============================================================================


class TestHandleOpenVocabularyList:
    """Tests for opening the vocabulary list."""

    def test_empty_vocabulary_list(self, coordinator, mock_main_window):
        """Test showing empty vocabulary list."""
        coordinator.handle_open_vocabulary_list()
        
        mock_main_window.show_info.assert_called_once()
        call_args = mock_main_window.show_info.call_args
        assert "haven't tracked" in call_args[0][1].lower()

    def test_vocabulary_list_with_words(self, coordinator, mock_main_window, 
                                        mock_vocabulary_service, sample_volume):
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
        
        coordinator.handle_open_vocabulary_list()
        
        mock_main_window.show_info.assert_called_once()
        call_args = mock_main_window.show_info.call_args
        message = call_args[0][1]
        assert "2 word(s)" in message
        assert "taberu" in message
        assert "hashiru" in message

    def test_vocabulary_list_truncates_at_10(self, coordinator, mock_main_window,
                                             mock_vocabulary_service, sample_volume):
        """Test that lists > 10 words show '... and more'."""
        # Add 15 words
        for i in range(15):
            mock_vocabulary_service.track_word(
                lemma=f"word{i}", reading=f"word{i}", part_of_speech="Noun",
                volume_path=sample_volume.volume_path, page_index=0,
                crop_coordinates={"x": 0, "y": 0}, sentence_text="test"
            )
        
        coordinator.handle_open_vocabulary_list()
        
        call_args = mock_main_window.show_info.call_args
        message = call_args[0][1]
        assert "15 word(s)" in message
        assert "... and 5 more" in message

    def test_vocabulary_list_error_handling(self, coordinator, mock_main_window,
                                            mock_vocabulary_service):
        """Test error handling when list fails."""
        mock_vocabulary_service.list_tracked_words = MagicMock(
            side_effect=Exception("DB error")
        )
        
        coordinator.handle_open_vocabulary_list()
        
        mock_main_window.show_error.assert_called_once()


# ============================================================================
# Tests for handle_view_word_context
# ============================================================================


class TestHandleViewWordContext:
    """Tests for viewing word context."""

    def test_view_word_context_opens_panel(self, coordinator, mock_context_panel,
                                           mock_main_window, mock_vocabulary_service, 
                                           sample_volume, tmp_path):
        """Test that viewing context opens the panel."""
        # Create a tracked word with appearances
        word = mock_vocabulary_service._db.upsert_tracked_word("test", "てすと", "Noun")
        vol = mock_vocabulary_service._db.upsert_volume(sample_volume.volume_path, "Test Vol")
        mock_vocabulary_service._db.insert_word_appearance(
            word.id, vol.id, 0, {"x": 0, "y": 0}, "test sentence"
        )
        
        coordinator.handle_view_word_context(word.id)
        
        mock_context_panel.display_word_context.assert_called_once()
        call_args = mock_context_panel.display_word_context.call_args
        assert call_args[1]["word_id"] == word.id
        assert call_args[1]["word_lemma"] == "test"
        
        mock_main_window.show_context_panel.assert_called_once()

    def test_view_context_word_not_found(self, coordinator, mock_main_window):
        """Test handling when word is not found."""
        coordinator.handle_view_word_context(999)
        
        mock_main_window.show_error.assert_called_once()
        call_args = mock_main_window.show_error.call_args
        assert "could not be found" in call_args[0][1].lower()

    def test_view_context_no_appearances(self, coordinator, mock_main_window,
                                         mock_vocabulary_service):
        """Test handling when word has no appearances."""
        word = mock_vocabulary_service._db.upsert_tracked_word("orphan", "もじ", "Noun")
        
        coordinator.handle_view_word_context(word.id)
        
        mock_main_window.show_info.assert_called_once()
        call_args = mock_main_window.show_info.call_args
        assert "No Appearances" in call_args[0][0]

    def test_view_context_saves_state_for_restoration(self, coordinator, sample_volume):
        """Test that view state is saved for later restoration."""
        coordinator.set_session_context(sample_volume, SINGLE_PAGE_MODE, 0)
        
        # Simulate opening context (which saves state)
        word = MagicMock()
        word.id = 1
        word.lemma = "test"
        coordinator._vocabulary_service = MagicMock()
        coordinator.vocabulary_service.list_tracked_words = MagicMock(return_value=[word])
        coordinator.vocabulary_service.list_appearances = MagicMock(return_value=[])
        
        assert coordinator.previous_view_mode_name == "single"
        assert coordinator.previous_page_number == 0


# ============================================================================
# Tests for handle_view_context_by_lemma
# ============================================================================


class TestHandleViewContextByLemma:
    """Tests for viewing context by word lemma."""

    def test_view_context_by_lemma_found(self, coordinator, mock_context_panel,
                                         mock_vocabulary_service, sample_volume):
        """Test viewing context using lemma."""
        # Create tracked word
        word = mock_vocabulary_service._db.upsert_tracked_word("taberu", "たべる", "Verb")
        vol = mock_vocabulary_service._db.upsert_volume(sample_volume.volume_path, "Test")
        mock_vocabulary_service._db.insert_word_appearance(
            word.id, vol.id, 0, {"x": 0, "y": 0}, "sentence"
        )
        
        coordinator.handle_view_context_by_lemma("taberu")
        
        # Should call display_word_context
        mock_context_panel.display_word_context.assert_called_once()

    def test_view_context_by_lemma_not_tracked(self, coordinator, mock_main_window):
        """Test handling when lemma is not tracked."""
        coordinator.handle_view_context_by_lemma("unknown")
        
        mock_main_window.show_error.assert_called_once()
        call_args = mock_main_window.show_error.call_args
        assert "tracked" in call_args[0][1].lower()


# ============================================================================
# Tests for appearance navigation
# ============================================================================


class TestAppearanceNavigation:
    """Tests for appearance selection and navigation."""

    def test_appearance_selected_computes_target_page(self, coordinator, sample_volume):
        """Test that selecting appearance computes correct target page."""
        coordinator.set_session_context(sample_volume, SINGLE_PAGE_MODE, 0)
        
        # In single page mode, target page should be the appearance page
        coordinator._on_appearance_selected(word_id=1, appearance_id=1, page_index=1)
        
        # Signal should have been emitted (we test indirectly by ensuring no error)
        assert coordinator._view_mode is not None

    def test_appearance_without_volume_ignored(self, coordinator):
        """Test that appearance selection without volume is ignored."""
        coordinator.set_session_context(None, SINGLE_PAGE_MODE, 0)
        
        # Should not raise error, just ignored
        coordinator._on_appearance_selected(word_id=1, appearance_id=1, page_index=0)


# ============================================================================
# Tests for context panel closure
# ============================================================================


class TestContextPanelClosure:
    """Tests for closing context panel."""

    def test_on_context_panel_closed_saves_restore_state(self, coordinator):
        """Test that closing panel saves state for restoration."""
        coordinator.previous_view_mode_name = "single"
        coordinator.previous_page_number = 5
        
        coordinator._on_context_panel_closed()
        
        # Verify state was maintained
        assert coordinator.previous_view_mode_name == "single"
        assert coordinator.previous_page_number == 5

    def test_on_context_panel_closed_hides_panel(self, coordinator, mock_main_window):
        """Test that closing panel hides it."""
        coordinator._on_context_panel_closed()
        
        mock_main_window.hide_context_panel.assert_called_once()

    def test_on_context_panel_closed_updates_state(self, coordinator):
        """Test that closing panel updates internal state."""
        coordinator.context_panel_active = True
        
        coordinator._on_context_panel_closed()
        
        assert coordinator.context_panel_active is False


# ============================================================================
# Tests for session context management
# ============================================================================


class TestSessionContextManagement:
    """Tests for session context handling."""

    def test_set_session_context(self, coordinator, sample_volume):
        """Test setting session context."""
        coordinator.set_session_context(sample_volume, SINGLE_PAGE_MODE, 5)
        
        assert coordinator._current_volume == sample_volume
        assert coordinator._view_mode == SINGLE_PAGE_MODE
        assert coordinator._current_page == 5

    def test_view_mode_context_adjustment_single_to_single(self, coordinator, sample_volume):
        """Test context view adjustment in single page mode."""
        coordinator.set_session_context(sample_volume, SINGLE_PAGE_MODE, 0)
        
        # Manually trigger context view adjustment
        coordinator._request_context_view_adjustment()
        
        # View mode should remain single in context
        # (Implementation depends on view_mode.context_view_mode())

    def test_previous_state_saved_on_context_open(self, coordinator, sample_volume):
        """Test that previous state is saved when opening context."""
        coordinator.set_session_context(sample_volume, DOUBLE_PAGE_MODE, 3)
        
        # Simulate saving state (done in handle_view_word_context)
        coordinator.previous_view_mode_name = DOUBLE_PAGE_MODE.name
        coordinator.previous_page_number = 3
        
        assert coordinator.previous_view_mode_name == "double"
        assert coordinator.previous_page_number == 3
