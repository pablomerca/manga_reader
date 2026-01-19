"""Unit tests for SentenceAnalysisCoordinator."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject

from manga_reader.coordinators import SentenceAnalysisCoordinator
from manga_reader.services import (
    InMemoryTranslationCache,
    SettingsManager,
    TranslationResult,
    CacheRecord,
)


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
def mock_translation_service():
    """Provide a mocked TranslationService."""
    service = MagicMock()
    service.translate = MagicMock()
    return service


@pytest.fixture
def settings_manager():
    """Provide a settings manager with test API key."""
    manager = MagicMock()
    manager.get_gemini_api_key = MagicMock(return_value=None)
    return manager


@pytest.fixture
def coordinator(mock_main_window, translation_cache, mock_translation_service, settings_manager):
    """Create a SentenceAnalysisCoordinator with mocked dependencies."""
    return SentenceAnalysisCoordinator(
        main_window=mock_main_window,
        translation_cache=translation_cache,
        translation_service=mock_translation_service,
        settings_manager=settings_manager,
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

    def test_actions_disabled_without_api_key(self, coordinator, settings_manager):
        """Actions should be disabled if API key is not set."""
        settings_manager.get_gemini_api_key.return_value = None
        coordinator.selected_block_text = "何か"
        assert not coordinator.actions_enabled()

    def test_actions_disabled_without_selected_block(self, coordinator, settings_manager):
        """Actions should be disabled if no block is selected."""
        settings_manager.get_gemini_api_key.return_value = "test-key-123"
        assert not coordinator.actions_enabled()

    def test_actions_enabled_with_api_key_and_selected_block(self, coordinator, settings_manager):
        """Actions should be enabled when API key and block are set."""
        settings_manager.get_gemini_api_key.return_value = "test-key-123"
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

    def test_request_translation_emits_started_signal(
        self, coordinator, mock_main_window, mock_translation_service, settings_manager
    ):
        """Translation request should emit started signal."""
        settings_manager.get_gemini_api_key.return_value = "test-key"
        coordinator.on_block_selected("何か", "vol1")
        
        mock_translation_service.translate.return_value = TranslationResult(
            text="Something",
            model="gemini-1.5-flash",
        )

        started_spy = MagicMock()
        coordinator.translation_started.connect(started_spy)

        coordinator.request_translation()
        started_spy.assert_called_once()

    def test_request_translation_with_cache_hit(
        self, coordinator, translation_cache, mock_translation_service, settings_manager
    ):
        """Translation should use cached result if available."""
        settings_manager.get_gemini_api_key.return_value = "test-key"
        coordinator.on_block_selected("何か", "vol1")
        
        cached_record = CacheRecord(
            normalized_text="何か",
            lang="en",
            translation="Something (cached)",
            explanation=None,
            model="gemini-pro",
            updated_at=datetime.now(),
        )
        translation_cache.put("vol1", "何か", "en", cached_record)

        completed_spy = MagicMock()
        coordinator.translation_completed.connect(completed_spy)

        coordinator.request_translation()
        completed_spy.assert_called_once_with("Something (cached)")
        mock_translation_service.translate.assert_not_called()

    def test_request_translation_with_cache_miss_calls_service(
        self, coordinator, mock_translation_service, settings_manager
    ):
        """Translation should call service on cache miss."""
        settings_manager.get_gemini_api_key.return_value = "test-key"
        coordinator.on_block_selected("何か", "vol1")
        
        mock_translation_service.translate.return_value = TranslationResult(
            text="Something",
            model="gemini-1.5-flash",
        )

        coordinator.request_translation()
        mock_translation_service.translate.assert_called_once_with(
            text="何か",
            api_key="test-key"
        )

    def test_request_translation_stores_result_in_cache(
        self, coordinator, translation_cache, mock_translation_service, settings_manager
    ):
        """Successful translation should be stored in cache."""
        settings_manager.get_gemini_api_key.return_value = "test-key"
        coordinator.on_block_selected("何か", "vol1")
        
        mock_translation_service.translate.return_value = TranslationResult(
            text="Something",
            model="gemini-1.5-flash",
        )

        coordinator.request_translation()
        
        cached = translation_cache.get("vol1", "何か", "en")
        assert cached is not None
        assert cached.translation == "Something"

    def test_request_translation_emits_error_on_failure(
        self, coordinator, mock_translation_service, settings_manager
    ):
        """Translation error should emit failed signal."""
        settings_manager.get_gemini_api_key.return_value = "test-key"
        coordinator.on_block_selected("何か", "vol1")
        
        mock_translation_service.translate.return_value = TranslationResult(
            text="",
            model="gemini-1.5-flash",
            error="API error occurred",
        )

        failed_spy = MagicMock()
        coordinator.translation_failed.connect(failed_spy)

        coordinator.request_translation()
        failed_spy.assert_called_once_with("API error occurred")

    def test_request_translation_fails_without_api_key(
        self, coordinator, mock_main_window, settings_manager
    ):
        """Translation request should fail without API key."""
        settings_manager.get_gemini_api_key.return_value = None
        coordinator.on_block_selected("何か", "vol1")

        coordinator.request_translation()
        mock_main_window.show_error.assert_called()

    def test_request_translation_fails_without_selected_block(
        self, coordinator, mock_main_window, settings_manager
    ):
        """Translation request should fail without selected block."""
        settings_manager.get_gemini_api_key.return_value = "test-key"

        coordinator.request_translation()
        mock_main_window.show_error.assert_called()

    def test_request_translation_fails_without_volume(
        self, coordinator, mock_main_window, settings_manager
    ):
        """Translation request should fail without current volume."""
        settings_manager.get_gemini_api_key.return_value = "test-key"
        coordinator.selected_block_text = "何か"
        coordinator.current_volume_id = None

        coordinator.request_translation()
        mock_main_window.show_error.assert_called()


class TestSentenceAnalysisCoordinatorExplanationRequest:
    """Tests for explanation request handling."""

    def test_request_explanation_succeeds_with_api_key_and_block(
        self, coordinator, mock_main_window, settings_manager
    ):
        """Explanation request should succeed when API key and block are set."""
        settings_manager.get_gemini_api_key.return_value = "test-key"
        coordinator.on_block_selected("何か", "vol1")

        signal_spy = MagicMock()
        coordinator.explanation_requested.connect(signal_spy)

        coordinator.request_explanation()
        signal_spy.assert_called_once_with("何か")
        mock_main_window.show_error.assert_not_called()

    def test_request_explanation_fails_without_api_key(
        self, coordinator, mock_main_window, settings_manager
    ):
        """Explanation request should fail without API key."""
        settings_manager.get_gemini_api_key.return_value = None
        coordinator.on_block_selected("何か", "vol1")

        signal_spy = MagicMock()
        coordinator.explanation_requested.connect(signal_spy)

        coordinator.request_explanation()
        signal_spy.assert_not_called()
        mock_main_window.show_error.assert_called()

    def test_request_explanation_fails_without_selected_block(
        self, coordinator, mock_main_window, settings_manager
    ):
        """Explanation request should fail without selected block."""
        settings_manager.get_gemini_api_key.return_value = "test-key"

        signal_spy = MagicMock()
        coordinator.explanation_requested.connect(signal_spy)

        coordinator.request_explanation()
        signal_spy.assert_not_called()
        mock_main_window.show_error.assert_called()

    def test_request_explanation_emits_selected_text(
        self, coordinator, mock_main_window, settings_manager
    ):
        """Explanation request should emit the selected block text."""
        settings_manager.get_gemini_api_key.return_value = "test-key"
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
