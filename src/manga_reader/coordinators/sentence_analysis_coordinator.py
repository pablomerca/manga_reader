"""Sentence Analysis Coordinator - Manages translate/explain workflow and panel state."""

from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from manga_reader.services import TranslationCache, SettingsManager
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

    # Signals
    block_selected = Signal(str)  # Emitted when a block is selected (pass original text)
    translation_requested = Signal(str)  # Emitted when user requests translation
    explanation_requested = Signal(str)  # Emitted when user requests explanation
    panel_closed = Signal()  # Emitted when user closes the panel

    def __init__(
        self,
        main_window: MainWindow,
        translation_cache: TranslationCache,
        settings_manager: SettingsManager,
    ):
        super().__init__()

        self.main_window = main_window
        self.translation_cache = translation_cache
        self.settings_manager = settings_manager

        # Panel state
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
        if not self._current_api_key():
            self.main_window.show_error("API key not configured")
            return

        self.translation_requested.emit(self.selected_block_text)

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
