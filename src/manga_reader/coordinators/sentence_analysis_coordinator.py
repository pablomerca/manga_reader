"""Sentence Analysis Coordinator - Manages translate/explain workflow and panel state."""

from datetime import datetime
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from manga_reader.services import (
    TranslationCache,
    TranslationService,
    SettingsManager,
    CacheRecord,
    normalize_text,
)
from manga_reader.ui import MainWindow


class SentenceAnalysisCoordinator(QObject):
    """
    Orchestrates the sentence analysis/translation workflow.

    Responsibilities:
    - Manage panel state (selected block text, actions enabled/disabled based on API key).
    - Handle translate and explain action requests.
    - Coordinate cache lookups and API calls via services.
    - Update panel UI with results, errors, loading states.
    """

    block_selected = Signal(str)
    translation_requested = Signal(str)
    explanation_requested = Signal(str)
    panel_closed = Signal()
    
    translation_started = Signal()
    translation_completed = Signal(str)
    translation_failed = Signal(str)

    def __init__(
        self,
        main_window: MainWindow,
        translation_cache: TranslationCache,
        translation_service: TranslationService,
        settings_manager: SettingsManager,
    ):
        super().__init__()

        self.main_window = main_window
        self.translation_cache = translation_cache
        self.translation_service = translation_service
        self.settings_manager = settings_manager

        self.selected_block_text: Optional[str] = None
        self.current_volume_id: Optional[str] = None

    def on_block_selected(self, block_text: str, volume_id: str) -> None:
        """
        Called when user clicks an OCR block.

        Args:
            block_text: Original Japanese text from the block.
            volume_id: Current volume identifier (for cache keying).
        """
        self.selected_block_text = block_text
        self.current_volume_id = volume_id
        self.block_selected.emit(block_text)

    def request_translation(self) -> None:
        """Request translation of the currently selected block."""
        if not self.selected_block_text:
            self.main_window.show_error("No block selected")
            return
        
        api_key = self._current_api_key()
        if not api_key:
            self.main_window.show_error("API key not configured. Add GEMINI_API_KEY to .env file.")
            return

        if not self.current_volume_id:
            self.main_window.show_error("No volume loaded")
            return

        self.translation_started.emit()
        
        normalized = normalize_text(self.selected_block_text)
        
        cached = self.translation_cache.get(
            volume_id=self.current_volume_id,
            normalized_text=normalized,
            lang="en"
        )
        
        if cached and cached.translation:
            self.translation_completed.emit(cached.translation)
            return
        
        result = self.translation_service.translate(
            text=self.selected_block_text,
            api_key=api_key
        )
        
        if result.is_error:
            self.translation_failed.emit(result.error or "Unknown error")
            return
        
        record = CacheRecord(
            normalized_text=normalized,
            lang="en",
            translation=result.text,
            explanation=None,
            model=result.model,
            updated_at=datetime.now(),
        )
        
        self.translation_cache.put(
            volume_id=self.current_volume_id,
            normalized_text=normalized,
            lang="en",
            record=record,
        )
        
        self.translation_completed.emit(result.text)

    def request_explanation(self) -> None:
        """Request explanation of the currently selected block."""
        if not self.selected_block_text:
            self.main_window.show_error("No block selected")
            return
        if not self._current_api_key():
            self.main_window.show_error("API key not configured")
            return

        self.explanation_requested.emit(self.selected_block_text)

    def on_panel_closed(self) -> None:
        """Called when user closes the panel."""
        self.selected_block_text = None
        self.panel_closed.emit()

    def actions_enabled(self) -> bool:
        """Return True if translation/explanation actions should be enabled."""
        return bool(self._current_api_key()) and self.selected_block_text is not None

    def _current_api_key(self) -> Optional[str]:
        """Fetch the latest API key from settings."""
        return self.settings_manager.get_gemini_api_key()
