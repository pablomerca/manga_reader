"""Dictionary Panel Coordinator - Manages dictionary panel lifecycle and breadcrumb navigation."""

from typing import List, Optional

from PySide6.QtCore import QObject, Slot

from manga_reader.core import MangaVolume
from manga_reader.services import (
    BreadcrumbItem,
    DictionaryService,
    KanjiEntry,
)
from manga_reader.ui import DictionaryPanel, MainWindow


class DictionaryPanelCoordinator(QObject):
    """
    Manages dictionary panel workflow: show definition, navigate kanji, breadcrumbs.

    Responsibilities:
    - Handle expand button signal from popup (show_full_definition)
    - Manage breadcrumb trail for word → kanji navigation
    - Handle kanji clicks and display kanji entries
    - Handle breadcrumb clicks to navigate back
    - Update on page/volume changes
    - Clear state on panel close
    """

    def __init__(
        self,
        panel: DictionaryPanel,
        dictionary_service: DictionaryService,
        main_window: MainWindow,
    ):
        super().__init__()

        self.panel = panel
        self.dictionary_service = dictionary_service
        self.main_window = main_window

        # Session context (provided by ReaderController)
        self._current_volume: Optional[MangaVolume] = None
        self._current_page: int = 0

        # Breadcrumb trail state
        self.breadcrumb_stack: List[BreadcrumbItem] = []

        # Wire panel signals
        self.panel.kanji_clicked.connect(self._on_kanji_clicked)
        self.panel.breadcrumb_clicked.connect(self._on_breadcrumb_clicked)
        self.panel.closed.connect(self._on_panel_closed)

    def set_session_context(self, volume: Optional[MangaVolume], current_page: int):
        """Update session context (called by ReaderController on page/volume change)."""
        self._current_volume = volume
        self._current_page = current_page

    @Slot(str)
    def handle_show_full_definition(self, lemma: str):
        """
        Show full definition panel for a word (triggered by popup expand button).

        Args:
            lemma: The word lemma/surface form to look up
        """
        try:
            # Lookup all entries
            result = self.dictionary_service.lookup_all_entries(lemma, lemma)

            if result is None:
                self.main_window.show_error(
                    "Lookup Failed",
                    f"Could not find definition for '{lemma}'.",
                )
                return

            # Initialize breadcrumb trail with word entry
            self.breadcrumb_stack = [
                BreadcrumbItem(
                    type="word",
                    content=result,
                    label=f"Word: {lemma}",
                    lemma=lemma,
                )
            ]

            # Display word entry
            self.panel.display_word_entry(result, lemma)
            self.panel.set_breadcrumbs(self.breadcrumb_stack)

            # Show the panel
            self.main_window.show_dictionary_panel()

        except Exception as e:
            self.main_window.show_error(
                "Dictionary Error",
                f"Error looking up '{lemma}': {e}",
            )

    @Slot(str)
    def _on_kanji_clicked(self, kanji: str):
        """
        Handle kanji click in word definition.

        Args:
            kanji: The kanji character clicked
        """
        try:
            # Lookup kanji
            kanji_entry = self.dictionary_service.lookup_kanji(kanji)

            if kanji_entry is None:
                self.main_window.show_error(
                    "Kanji Lookup Failed",
                    f"Could not find information for kanji '{kanji}'.",
                )
                return

            # Push current entry to breadcrumbs
            self.breadcrumb_stack.append(
                BreadcrumbItem(
                    type="kanji",
                    content=kanji_entry,
                    label=f"Kanji: {kanji}",
                    lemma=None,
                )
            )

            # Display kanji entry
            self.panel.display_kanji_entry(kanji_entry)
            self.panel.set_breadcrumbs(self.breadcrumb_stack)

        except Exception as e:
            self.main_window.show_error(
                "Dictionary Error",
                f"Error looking up kanji '{kanji}': {e}",
            )

    @Slot(int)
    def _on_breadcrumb_clicked(self, index: int):
        """
        Handle breadcrumb click - restore entry at index.

        Args:
            index: Index of breadcrumb to restore (0-based)
        """
        try:
            # Validate index
            if index < 0 or index >= len(self.breadcrumb_stack):
                return

            # Restore breadcrumb stack to this level (discard deeper items)
            self.breadcrumb_stack = self.breadcrumb_stack[:index + 1]
            restored_item = self.breadcrumb_stack[index]

            # Display appropriate entry type
            if restored_item.type == "word":
                # Display word entry
                self.panel.display_word_entry(restored_item.content, restored_item.lemma or "")
            elif restored_item.type == "kanji":
                # Display kanji entry
                self.panel.display_kanji_entry(restored_item.content)

            # Update breadcrumbs
            self.panel.set_breadcrumbs(self.breadcrumb_stack)

        except Exception as e:
            self.main_window.show_error(
                "Navigation Error",
                f"Error navigating breadcrumbs: {e}",
            )

    @Slot()
    def _on_panel_closed(self):
        """Handle panel close - clear breadcrumb history and hide panel."""
        self.breadcrumb_stack = []
        self.main_window.hide_dictionary_panel()

    @Slot(int)
    def handle_page_changed(self, page_index: int):
        """
        Handle page change in reader - update context, keep panel open.

        Args:
            page_index: New page index
        """
        self._current_page = page_index
        # Panel remains open; no other action needed

    @Slot()
    def handle_volume_changed(self):
        """Handle volume change in reader - close panel."""
        self.breadcrumb_stack = []
