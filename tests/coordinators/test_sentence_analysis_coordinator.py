"""Unit tests for SentenceAnalysisCoordinator."""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject

from manga_reader.coordinators import SentenceAnalysisCoordinator
from manga_reader.services import InMemoryTranslationCache, SettingsManager


@pytest.fixture
def mock_main_window():
    """Provide a mocked MainWindow."""
    window = MagicMock(spec=QObject)
    window.show_error = MagicMock()
    window.show_info = MagicMock()
    return window


@pytest.fixture
def translation_cache():
    """Provide a fresh in-memory cache."""
    return InMemoryTranslationCache()


@pytest.fixture
def coordinator(mock_main_window, translation_cache):
    """Create a SentenceAnalysisCoordinator with mocked dependencies."""
    return SentenceAnalysisCoordinator(
        main_window=mock_main_window,
        translation_cache=translation_cache,
        settings_manager=SettingsManager(),
    )


class TestSentenceAnalysisCoordinatorInitialization:
    """Tests for coordinator initialization and state."""

    def test_coordinator_initializes_with_no_api_key(self, coordinator):
        """Coordinator should start with no API key configured."""
        assert coordinator._current_api_key() is None

    def test_coordinator_initializes_with_no_selected_block(self, coordinator):
        """Coordinator should start with no selected block text."""
        assert coordinator.selected_block_text is None

    def test_coordinator_initializes_with_no_volume(self, coordinator):
        """Coordinator should start with no current volume."""
        assert coordinator.current_volume_id is None

    def test_actions_disabled_without_api_key(self, coordinator):
        """Actions should be disabled if API key is not set."""
        coordinator.selected_block_text = "何か"
        assert not coordinator.actions_enabled()

    def test_actions_disabled_without_selected_block(self, coordinator):
        """Actions should be disabled if no block is selected."""
        coordinator.settings_manager.set_gemini_api_key("test-key-123")
        assert not coordinator.actions_enabled()

    def test_actions_enabled_with_api_key_and_selected_block(self, coordinator):
        """Actions should be enabled when API key and block are set."""
        coordinator.settings_manager.set_gemini_api_key("test-key-123")
        coordinator.on_block_selected("何か", "vol1")
        assert coordinator.actions_enabled()


class TestSentenceAnalysisCoordinatorBlockSelection:
    """Tests for block selection and panel updates."""

    def test_on_block_selected_stores_text_and_volume(self, coordinator):
        """on_block_selected should store the text and volume ID."""
        coordinator.on_block_selected("何か", "vol1")
        assert coordinator.selected_block_text == "何か"
        assert coordinator.current_volume_id == "vol1"

    def test_on_block_selected_emits_signal(self, coordinator):
        """on_block_selected should emit block_selected signal with text."""
        signal_spy = MagicMock()
        coordinator.block_selected.connect(signal_spy)

        coordinator.on_block_selected("何か", "vol1")
        signal_spy.assert_called_once()

    def test_on_block_selected_replaces_previous_selection(self, coordinator):
        """Selecting a new block should replace the previous one."""
        coordinator.on_block_selected("最初", "vol1")
        assert coordinator.selected_block_text == "最初"

        coordinator.on_block_selected("次", "vol1")
        assert coordinator.selected_block_text == "次"


class TestSentenceAnalysisCoordinatorTranslationRequest:
    """Tests for translation request handling."""

    def test_request_translation_succeeds_with_api_key_and_block(
        self, coordinator, mock_main_window
    ):
        """Translation request should succeed when API key and block are set."""
        coordinator.settings_manager.set_gemini_api_key("test-key")
        coordinator.on_block_selected("何か", "vol1")

        signal_spy = MagicMock()
        coordinator.translation_requested.connect(signal_spy)

        coordinator.request_translation()
        signal_spy.assert_called_once_with("何か")
        mock_main_window.show_error.assert_not_called()

    def test_request_translation_fails_without_api_key(
        self, coordinator, mock_main_window
    ):
        """Translation request should fail without API key."""
        coordinator.on_block_selected("何か", "vol1")

        signal_spy = MagicMock()
        coordinator.translation_requested.connect(signal_spy)

        coordinator.request_translation()
        signal_spy.assert_not_called()
        mock_main_window.show_error.assert_called()

    def test_request_translation_fails_without_selected_block(
        self, coordinator, mock_main_window
    ):
        """Translation request should fail without selected block."""
        coordinator.settings_manager.set_gemini_api_key("test-key")

        signal_spy = MagicMock()
        coordinator.translation_requested.connect(signal_spy)

        coordinator.request_translation()
        signal_spy.assert_not_called()
        mock_main_window.show_error.assert_called()

    def test_request_translation_emits_selected_text(
        self, coordinator, mock_main_window
    ):
        """Translation request should emit the selected block text."""
        coordinator.settings_manager.set_gemini_api_key("test-key")
        coordinator.on_block_selected("走っている", "vol1")

        signal_spy = MagicMock()
        coordinator.translation_requested.connect(signal_spy)

        coordinator.request_translation()
        signal_spy.assert_called_once_with("走っている")


class TestSentenceAnalysisCoordinatorExplanationRequest:
    """Tests for explanation request handling."""

    def test_request_explanation_succeeds_with_api_key_and_block(
        self, coordinator, mock_main_window
    ):
        """Explanation request should succeed when API key and block are set."""
        coordinator.settings_manager.set_gemini_api_key("test-key")
        coordinator.on_block_selected("何か", "vol1")

        signal_spy = MagicMock()
        coordinator.explanation_requested.connect(signal_spy)

        coordinator.request_explanation()
        signal_spy.assert_called_once_with("何か")
        mock_main_window.show_error.assert_not_called()

    def test_request_explanation_fails_without_api_key(
        self, coordinator, mock_main_window
    ):
        """Explanation request should fail without API key."""
        coordinator.on_block_selected("何か", "vol1")

        signal_spy = MagicMock()
        coordinator.explanation_requested.connect(signal_spy)

        coordinator.request_explanation()
        signal_spy.assert_not_called()
        mock_main_window.show_error.assert_called()

    def test_request_explanation_fails_without_selected_block(
        self, coordinator, mock_main_window
    ):
        """Explanation request should fail without selected block."""
        coordinator.settings_manager.set_gemini_api_key("test-key")

        signal_spy = MagicMock()
        coordinator.explanation_requested.connect(signal_spy)

        coordinator.request_explanation()
        signal_spy.assert_not_called()
        mock_main_window.show_error.assert_called()

    def test_request_explanation_emits_selected_text(
        self, coordinator, mock_main_window
    ):
        """Explanation request should emit the selected block text."""
        coordinator.settings_manager.set_gemini_api_key("test-key")
        coordinator.on_block_selected("走っている", "vol1")

        signal_spy = MagicMock()
        coordinator.explanation_requested.connect(signal_spy)

        coordinator.request_explanation()
        signal_spy.assert_called_once_with("走っている")


class TestSentenceAnalysisCoordinatorPanelLifecycle:
    """Tests for panel open/close lifecycle."""

    def test_on_panel_closed_clears_selection(self, coordinator):
        """on_panel_closed should clear the selected block text."""
        coordinator.on_block_selected("何か", "vol1")
        assert coordinator.selected_block_text == "何か"

        coordinator.on_panel_closed()
        assert coordinator.selected_block_text is None

    def test_on_panel_closed_emits_signal(self, coordinator):
        """on_panel_closed should emit panel_closed signal."""
        signal_spy = MagicMock()
        coordinator.panel_closed.connect(signal_spy)

        coordinator.on_panel_closed()
        signal_spy.assert_called_once()

    def test_panel_reopened_after_close(self, coordinator):
        """Panel should be able to open after being closed."""
        coordinator.on_block_selected("最初", "vol1")
        coordinator.on_panel_closed()

        coordinator.on_block_selected("次", "vol1")
        assert coordinator.selected_block_text == "次"
        assert coordinator.current_volume_id == "vol1"
