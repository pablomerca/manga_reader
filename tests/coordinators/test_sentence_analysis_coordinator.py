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
    ExplanationResult,
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
def mock_explanation_service():
    """Provide a mocked ExplanationService."""
    service = MagicMock()
    service.explain = MagicMock()
    return service


@pytest.fixture
def coordinator(mock_main_window, translation_cache, mock_translation_service, mock_explanation_service, settings_manager):
    """Create a SentenceAnalysisCoordinator with mocked dependencies."""
    return SentenceAnalysisCoordinator(
        main_window=mock_main_window,
        translation_cache=translation_cache,
        translation_service=mock_translation_service,
        explanation_service=mock_explanation_service,
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

    def test_explanation_uses_cached_value(
        self, coordinator, translation_cache, settings_manager, mock_translation_service, mock_explanation_service
    ):
        """If explanation is cached, services should not be called."""
        settings_manager.get_gemini_api_key.return_value = "key"
        coordinator.on_block_selected("何か", "vol1")

        cached_record = CacheRecord(
            normalized_text="何か",
            lang="en",
            translation="Something cached",
            explanation="Cached explanation",
            model="gemini-2.0-flash",
            updated_at=datetime.now(),
        )
        translation_cache.put("vol1", "何か", "en", cached_record)

        completed_spy = MagicMock()
        coordinator.explanation_completed.connect(completed_spy)

        coordinator.request_explanation()

        completed_spy.assert_called_once_with("Cached explanation")
        mock_translation_service.translate.assert_not_called()
        mock_explanation_service.explain.assert_not_called()

    def test_explanation_fetches_translation_if_missing(
        self, coordinator, settings_manager, mock_translation_service, mock_explanation_service, translation_cache
    ):
        """When translation is not cached, explanation flow should fetch it first."""
        settings_manager.get_gemini_api_key.return_value = "key"
        coordinator.on_block_selected("何か", "vol1")

        mock_translation_service.translate.return_value = TranslationResult(
            text="Something",
            model="gemini-2.0-flash",
        )
        mock_explanation_service.explain.return_value = ExplanationResult(
            text="Explanation text",
            model="gemini-2.0-flash",
        )

        completed_spy = MagicMock()
        coordinator.explanation_completed.connect(completed_spy)

        coordinator.request_explanation()

        mock_translation_service.translate.assert_called_once()
        mock_explanation_service.explain.assert_called_once_with(
            original_jp="何か",
            translation_en="Something",
            api_key="key",
        )
        completed_spy.assert_called_once_with("Explanation text")

        cached = translation_cache.get("vol1", "何か", "en")
        assert cached is not None
        assert cached.translation == "Something"
        assert cached.explanation == "Explanation text"

    def test_explanation_uses_cached_translation_to_skip_translate_call(
        self, coordinator, translation_cache, settings_manager, mock_translation_service, mock_explanation_service
    ):
        """If translation is cached, explanation should skip translation service."""
        settings_manager.get_gemini_api_key.return_value = "key"
        coordinator.on_block_selected("走る", "vol1")

        cached_record = CacheRecord(
            normalized_text="走る",
            lang="en",
            translation="to run",
            explanation=None,
            model="gemini-2.0-flash",
            updated_at=datetime.now(),
        )
        translation_cache.put("vol1", "走る", "en", cached_record)

        mock_explanation_service.explain.return_value = ExplanationResult(
            text="Explain cached translation",
            model="gemini-2.0-flash",
        )

        coordinator.request_explanation()

        mock_translation_service.translate.assert_not_called()
        mock_explanation_service.explain.assert_called_once_with(
            original_jp="走る",
            translation_en="to run",
            api_key="key",
        )

    def test_explanation_fails_when_translation_fails_without_cache(
        self, coordinator, settings_manager, mock_translation_service, mock_main_window
    ):
        """Translation failure without cache should emit explanation_failed."""
        settings_manager.get_gemini_api_key.return_value = "key"
        coordinator.on_block_selected("何か", "vol1")

        mock_translation_service.translate.return_value = TranslationResult(
            text="",
            model="gemini-2.0-flash",
            error="API down",
        )

        failed_spy = MagicMock()
        coordinator.explanation_failed.connect(failed_spy)

        coordinator.request_explanation()

        failed_spy.assert_called_once_with("API down")

    def test_explanation_failure_emits_error(
        self, coordinator, settings_manager, mock_translation_service, mock_explanation_service
    ):
        """Explanation failure should emit failed signal even when translation succeeded."""
        settings_manager.get_gemini_api_key.return_value = "key"
        coordinator.on_block_selected("何か", "vol1")

        mock_translation_service.translate.return_value = TranslationResult(
            text="Something",
            model="gemini-2.0-flash",
        )
        mock_explanation_service.explain.return_value = ExplanationResult(
            text=None,
            model="gemini-2.0-flash",
            error="No output",
        )

        failed_spy = MagicMock()
        coordinator.explanation_failed.connect(failed_spy)

        coordinator.request_explanation()

        failed_spy.assert_called_once_with("No output")

    def test_explanation_requires_api_key(
        self, coordinator, mock_main_window, settings_manager
    ):
        """Missing API key should block explanation flow."""
        settings_manager.get_gemini_api_key.return_value = None
        coordinator.on_block_selected("何か", "vol1")

        coordinator.request_explanation()

        mock_main_window.show_error.assert_called()

    def test_explanation_requires_selected_block(
        self, coordinator, mock_main_window, settings_manager
    ):
        """Missing selection should block explanation flow."""
        settings_manager.get_gemini_api_key.return_value = "key"

        coordinator.request_explanation()

        mock_main_window.show_error.assert_called()

    def test_explanation_requires_volume(
        self, coordinator, mock_main_window, settings_manager
    ):
        """Missing volume should block explanation flow."""
        settings_manager.get_gemini_api_key.return_value = "key"
        coordinator.selected_block_text = "何か"
        coordinator.current_volume_id = None

        coordinator.request_explanation()

        mock_main_window.show_error.assert_called()


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
