"""Context Panel Coordinator - Manages word context panel lifecycle and navigation requests."""

from typing import Optional

from PySide6.QtCore import QObject, Slot, Signal

from manga_reader.core import MangaVolume
from manga_reader.services import VocabularyService
from manga_reader.ui import MainWindow, WordContextPanel

from .view_modes import ViewMode


class ContextPanelCoordinator(QObject):
    """
    Manages the context panel workflow: open, navigate, close.

    Responsibilities:
    - Open context panel for a word or lemma
    - Handle appearance selection (navigation requests)
    - Close context panel and request restoration to previous state
    - Request view mode/page adjustment when entering context view
    """

    # Signals to request actions from ReaderController
    navigate_to_page_requested = Signal(int)  # page_index
    view_mode_change_requested = Signal(str, int)  # mode_name, target_page
    restore_view_requested = Signal(str, int)  # mode_name, page_number

    def __init__(
        self,
        context_panel: WordContextPanel,
        vocabulary_service: VocabularyService,
        main_window: MainWindow,
    ):
        super().__init__()

        self.context_panel = context_panel
        self.vocabulary_service = vocabulary_service
        self.main_window = main_window

        # Previous state for restoration
        self.previous_view_mode_name: str = "single"
        self.previous_page_number: int = 0
        self.context_panel_active: bool = False

        # Current session context (provided by ReaderController)
        self._current_volume: Optional[MangaVolume] = None
        self._current_page: int = 0
        self._view_mode: Optional[ViewMode] = None

    def set_session_context(self, volume: Optional[MangaVolume], view_mode: ViewMode, current_page: int):
        """Update the current session context (called by ReaderController)."""
        self._current_volume = volume
        self._view_mode = view_mode
        self._current_page = current_page

    @Slot()
    def handle_open_vocabulary_list(self):
        """Open basic vocabulary list info in a dialog (MVP)."""
        try:
            tracked_words = self.vocabulary_service.list_tracked_words()
            if not tracked_words:
                self.main_window.show_info(
                    "Vocabulary List",
                    "You haven't tracked any words yet.\n\n"
                    "Click on a word in the manga and use the 'Track' button.",
                )
                return

            word_list = "\n".join(
                f"• {w.lemma} ({w.reading}) - {w.part_of_speech}"
                for w in tracked_words[:10]
            )
            more_text = (
                f"\n... and {len(tracked_words) - 10} more"
                if len(tracked_words) > 10
                else ""
            )
            self.main_window.show_info(
                "Vocabulary List",
                f"You have tracked {len(tracked_words)} word(s):\n\n{word_list}{more_text}",
            )
        except Exception as e:
            self.main_window.show_error("List Failed", f"Could not retrieve vocabulary list: {e}")

    @Slot(str)
    def handle_view_context_by_lemma(self, lemma: str):
        """Open context panel by lemma of a tracked word."""
        try:
            tracked_words = self.vocabulary_service.list_tracked_words()
            tracked_word = next((w for w in tracked_words if w.lemma == lemma), None)
            if not tracked_word:
                self.main_window.show_error(
                    "Word Not Tracked",
                    f"'{lemma}' is not yet tracked. Please track it first.",
                )
                return
            self.handle_view_word_context(tracked_word.id)
        except Exception as e:
            self.main_window.show_error("Context Lookup Failed", f"Could not retrieve word appearances: {e}")

    @Slot(int)
    def handle_view_word_context(self, word_id: int):
        """Open context panel showing all appearances of a tracked word."""
        try:
            tracked_words = self.vocabulary_service.list_tracked_words()
            tracked_word = next((w for w in tracked_words if w.id == word_id), None)
            if not tracked_word:
                self.main_window.show_error(
                    "Word Not Found",
                    "The requested word could not be found in vocabulary.",
                )
                return

            appearances = self.vocabulary_service.list_appearances(word_id)
            if not appearances:
                self.main_window.show_info(
                    "No Appearances",
                    f"The word '{tracked_word.lemma}' has no recorded appearances.",
                )
                return

            # Display panel
            self.context_panel.display_word_context(
                word_id=word_id,
                word_lemma=tracked_word.lemma,
                appearances=appearances,
            )

            # Save current view mode and page number for restoration
            if self._view_mode is not None:
                self.previous_view_mode_name = self._view_mode.name
            self.previous_page_number = self._current_page
            self.context_panel_active = True

            # Show the context panel
            self.main_window.show_context_panel()

            # Request context view adjustment
            self._request_context_view_adjustment()
        except Exception as e:
            self.main_window.show_error("Context Lookup Failed", f"Could not retrieve word appearances: {e}")

    @Slot()
    def _on_context_panel_closed(self):
        """Handle when user closes the context panel: request restoration."""
        self.context_panel_active = False
        self.main_window.hide_context_panel()
        self.restore_view_requested.emit(self.previous_view_mode_name, self.previous_page_number)

    @Slot(int, int, int)
    def _on_appearance_selected(self, word_id: int, appearance_id: int, page_index: int):
        """Handle when user selects an appearance: request navigation to that page."""
        if self._current_volume is None or self._view_mode is None:
            return

        # Compute target page respecting double-page semantics
        target_page = self._view_mode.page_for_appearance(
            self._current_volume,
            page_index,
            self._current_page,
        )
        self.navigate_to_page_requested.emit(target_page)

    def _request_context_view_adjustment(self):
        """Request view mode/page adjustment when entering context panel."""
        if self._view_mode is None:
            return

        current_before_context = self._current_page
        target_page = self._view_mode.page_for_context(
            current_page_number=self._current_page,
            last_clicked_page_index=self._current_page,
        )
        context_mode = self._view_mode.context_view_mode()

        self.view_mode_change_requested.emit(context_mode.name, target_page)
