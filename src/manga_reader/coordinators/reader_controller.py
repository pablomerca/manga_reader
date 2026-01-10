"""Reader Controller - Central coordinator for the reading session."""

from pathlib import Path

from PySide6.QtCore import QObject, Slot

from manga_reader.core import MangaVolume
from manga_reader.io import VolumeIngestor
from manga_reader.services import DictionaryService, VocabularyService
from manga_reader.ui import MainWindow, MangaCanvas, WordContextPanel
from .word_interaction_coordinator import WordInteractionCoordinator
from .context_panel_coordinator import ContextPanelCoordinator

from .view_modes import (
    ViewMode,
    create_view_mode,
    SINGLE_PAGE_MODE,
)


class ReaderController(QObject):
    """
    Central Nervous System of the application.
    Manages live session state and routes signals between UI and services.
    """
    
    def __init__(
        self,
        main_window: MainWindow,
        canvas: MangaCanvas,
        ingestor: VolumeIngestor,
        dictionary_service: DictionaryService,
        vocabulary_service: VocabularyService,
        context_panel: WordContextPanel,
        word_interaction: WordInteractionCoordinator | None = None,
        context_coordinator: ContextPanelCoordinator | None = None,
    ):
        super().__init__()
        
        self.main_window = main_window
        self.canvas = canvas
        self.ingestor = ingestor
        self.dictionary_service = dictionary_service
        self.vocabulary_service = vocabulary_service
        self.context_panel = context_panel
        self.word_interaction = word_interaction
        self.context_coordinator = context_coordinator
        
        # Session state
        self.current_volume: MangaVolume | None = None
        self.current_page_number: int = 0
        self.view_mode: ViewMode = SINGLE_PAGE_MODE
        self.previous_view_mode: ViewMode = self.view_mode
        self.previous_page_number: int = 0  # For restoring page when context closes from double mode
        self.context_panel_active: bool = False  # Track if context panel is open
        
        # Store context of the last clicked word for tracking (fallback compatibility)
        self.last_clicked_lemma: str | None = None
        self.last_clicked_page_index: int | None = None
        self.last_clicked_block_text: str | None = None  # Text from the block where word was clicked
        
        # Wire context panel signals (keep for backward compatibility)
        self.context_panel.closed.connect(self._on_context_panel_closed)
        self.context_panel.appearance_selected.connect(self._on_appearance_selected)

        # If a context coordinator is provided, wire its requests to handler slots
        if self.context_coordinator is not None:
            self.context_coordinator.navigate_to_page_requested.connect(self._handle_navigate_to_page_request)
            self.context_coordinator.view_mode_change_requested.connect(self._handle_view_mode_change_request)
            self.context_coordinator.restore_view_requested.connect(self._handle_restore_view_request)
    
    @Slot(Path)
    def handle_volume_opened(self, volume_path: Path):
        """
        Handle when user selects a volume folder.
        
        Args:
            volume_path: Path to the selected volume directory
        """
        # Ingest the volume
        volume = self.ingestor.ingest_volume(volume_path)
        
        if volume is None:
            self.main_window.show_error(
                "Volume Load Error",
                f"Failed to load volume from:\n{volume_path}"
            )
            return
        
        if volume.total_pages == 0:
            self.main_window.show_error(
                "Empty Volume",
                f"No pages found in:\n{volume_path}"
            )
            return
        
        # Update session state
        self.current_volume = volume
        self.current_page_number = 0
        
        # Render the first page
        self._render_current_page()
        
        # Show success message
        self.main_window.show_info(
            "Volume Loaded",
            f"Successfully loaded: {volume.title}\n"
            f"Total pages: {volume.total_pages}"
        )
    
    def _render_current_page(self):
        """Render the current page(s) to the canvas based on view mode."""
        if self.current_volume is None:
            return
        
        pages_to_render = self.view_mode.pages_to_render(
            self.current_volume,
            self.current_page_number,
        )
        if pages_to_render:
            self.canvas.render_pages(pages_to_render)
            # Keep coordinators in sync with current session context
            if self.word_interaction is not None:
                self.word_interaction.set_volume_context(self.current_volume, self.current_page_number)
            if self.context_coordinator is not None:
                self.context_coordinator.set_session_context(self.current_volume, self.view_mode, self.current_page_number)
        else:
            self.canvas.hide_dictionary_popup()

    # Backwards-compatible delegating slots for tests and legacy wiring
    @Slot(str, str, int, int, int, int)
    def handle_word_clicked(
        self,
        lemma: str,
        surface: str,
        mouse_x: int,
        mouse_y: int,
        page_index: int = -1,
        block_id: int = -1,
    ):
        """Delegate word click handling to WordInteractionCoordinator."""
        if self.word_interaction is not None:
            self.word_interaction.handle_word_clicked(
                lemma, surface, mouse_x, mouse_y, page_index, block_id
            )
            return

        # Fallback: original inline logic for backward compatibility in tests
        if self.dictionary_service is None:
            return

        self.last_clicked_lemma = lemma
        self.last_clicked_page_index = page_index if page_index >= 0 else self.current_page_number
        self.last_clicked_block_text = None

        if self.current_volume is not None:
            current_page = self.current_volume.get_page(self.last_clicked_page_index)
            if current_page is not None:
                clicked_block = None
                if block_id is not None and block_id >= 0 and block_id < len(current_page.ocr_blocks):
                    clicked_block = current_page.ocr_blocks[block_id]
                else:
                    clicked_block = current_page.find_block_at_position(mouse_x, mouse_y)
                if clicked_block is not None:
                    self.last_clicked_block_text = clicked_block.full_text

        entry = self.dictionary_service.lookup(lemma, surface)
        is_tracked = self.vocabulary_service.is_word_tracked(lemma)

        payload = {
            "surface": surface or lemma,
            "reading": entry.reading if entry else "",
            "senses": [
                {"glosses": sense.glosses, "pos": sense.pos}
                for sense in entry.senses
            ] if entry else [],
            "mouseX": mouse_x,
            "mouseY": mouse_y,
            "notFound": entry is None,
            "isTracked": is_tracked,
            "lemma": lemma,
        }

        self.canvas.show_dictionary_popup(payload)

    @Slot(str, str, str)
    def handle_track_word(self, lemma: str, reading: str, part_of_speech: str):
        """Delegate track word handling to WordInteractionCoordinator."""
        if self.word_interaction is not None:
            self.word_interaction.handle_track_word(lemma, reading, part_of_speech)
            return

        # Fallback: original inline logic for backward compatibility in tests
        if self.current_volume is None:
            self.main_window.show_error(
                "No Volume Open",
                "Please open a manga volume before tracking words.",
            )
            return

        page_index = self.last_clicked_page_index if self.last_clicked_page_index is not None else self.current_page_number
        current_page = self.current_volume.get_page(page_index)
        if not current_page:
            return

        if self.last_clicked_block_text:
            sentence = self.last_clicked_block_text
        else:
            sentence = current_page.get_all_text()

        crop_coords = {"x": 0, "y": 0, "width": 100, "height": 50}

        try:
            self.vocabulary_service.track_word(
                lemma=lemma,
                reading=reading,
                part_of_speech=part_of_speech,
                volume_path=self.current_volume.volume_path,
                page_index=page_index,
                crop_coordinates=crop_coords,
                sentence_text=sentence,
            )

            self.main_window.show_info(
                "Word Tracked",
                f"Added '{lemma}' to your vocabulary!\nReading: {reading}\nType: {part_of_speech}",
            )
        except Exception as e:
            self.main_window.show_error(
                "Tracking Failed",
                f"Could not track word: {e}",
            )
    
    def next_page(self):
        """Navigate to the next page, skipping appropriately in double page mode."""
        if self.current_volume is None:
            return
        
        next_page_num = self.view_mode.next_page_number(
            self.current_volume,
            self.current_page_number,
        )
        
        if next_page_num != self.current_page_number:
            self.current_page_number = next_page_num
            self._render_current_page()
    
    def previous_page(self):
        """Navigate to the previous page, accounting for double page mode."""
        if self.current_volume is None:
            return
        
        if self.current_page_number > 0:
            prev_page_num = self.view_mode.previous_page_number(
                self.current_volume,
                self.current_page_number,
            )
            
            if prev_page_num != self.current_page_number:
                self.current_page_number = prev_page_num
                self._render_current_page()
    
    def jump_to_page(self, page_number: int):
        """
        Jump to a specific page.
        
        Args:
            page_number: The page number to jump to (0-indexed)
        """
        if self.current_volume is None:
            return
        
        if 0 <= page_number < self.current_volume.total_pages:
            self.current_page_number = page_number
            self._render_current_page()
    
    @Slot(str)
    def handle_view_mode_changed(self, mode: str):
        """
        Handle view mode change from the UI.
        
        Args:
            mode: Either "single" or "double"
        """
        new_mode = create_view_mode(mode)
        if new_mode is None:
            return
        
        # Update mode and re-render
        self.view_mode = new_mode
        self._render_current_page()

    # Slots to handle requests from ContextPanelCoordinator
    @Slot(int)
    def _handle_navigate_to_page_request(self, page_index: int):
        """Handle navigation request from ContextPanelCoordinator."""
        self.jump_to_page(page_index)

    @Slot(str, int)
    def _handle_view_mode_change_request(self, mode_name: str, target_page: int):
        """Handle view mode change request from ContextPanelCoordinator."""
        new_mode = create_view_mode(mode_name)
        if new_mode:
            self.view_mode = new_mode
            self.current_page_number = target_page
            self._render_current_page()

    @Slot(str, int)
    def _handle_restore_view_request(self, mode_name: str, page_number: int):
        """Handle request to restore previous view state."""
        new_mode = create_view_mode(mode_name)
        if new_mode:
            self.view_mode = new_mode
            self.current_page_number = page_number
            self._render_current_page()

    # Word interaction is delegated to WordInteractionCoordinator

    @Slot(str)
    def handle_view_context_by_lemma(self, lemma: str):
        """Delegate to ContextPanelCoordinator if available, else inline logic."""
        if self.context_coordinator is not None:
            self.context_coordinator.handle_view_context_by_lemma(lemma)
            return
        try:
            tracked_words = self.vocabulary_service.list_tracked_words()
            tracked_word = next((w for w in tracked_words if w.lemma == lemma), None)
            if not tracked_word:
                self.main_window.show_error("Word Not Tracked", f"'{lemma}' is not yet tracked. Please track it first.")
                return
            self.handle_view_word_context(tracked_word.id)
        except Exception as e:
            self.main_window.show_error("Context Lookup Failed", f"Could not retrieve word appearances: {e}")

    @Slot()
    def handle_open_vocabulary_list(self):
        """Delegate to ContextPanelCoordinator if available, else inline logic."""
        if self.context_coordinator is not None:
            self.context_coordinator.handle_open_vocabulary_list()
            return
        try:
            tracked_words = self.vocabulary_service.list_tracked_words()
            if not tracked_words:
                self.main_window.show_info(
                    "Vocabulary List",
                    "You haven't tracked any words yet.\n\n"
                    "Click on a word in the manga and use the 'Track' button.",
                )
            else:
                word_list = "\n".join(
                    f"• {w.lemma} ({w.reading}) - {w.part_of_speech}"
                    for w in tracked_words[:10]
                )
                more_text = f"\n... and {len(tracked_words) - 10} more" if len(tracked_words) > 10 else ""
                self.main_window.show_info(
                    "Vocabulary List",
                    f"You have tracked {len(tracked_words)} word(s):\n\n{word_list}{more_text}",
                )
        except Exception as e:
            self.main_window.show_error("List Failed", f"Could not retrieve vocabulary list: {e}")

    # TODO: make more efficient
    @Slot(int)
    def handle_view_word_context(self, word_id: int):
        """Delegate to ContextPanelCoordinator if available, else inline logic."""
        if self.context_coordinator is not None:
            self.context_coordinator.handle_view_word_context(word_id)
            return
        try:
            tracked_words = self.vocabulary_service.list_tracked_words()
            tracked_word = next((w for w in tracked_words if w.id == word_id), None)
            if not tracked_word:
                self.main_window.show_error("Word Not Found", "The requested word could not be found in vocabulary.")
                return
            appearances = self.vocabulary_service.list_appearances(word_id)
            if not appearances:
                self.main_window.show_info("No Appearances", f"The word '{tracked_word.lemma}' has no recorded appearances.")
                return
            self.context_panel.display_word_context(
                word_id=word_id, word_lemma=tracked_word.lemma, appearances=appearances
            )
            self.previous_view_mode = self.view_mode
            self.previous_page_number = self.current_page_number
            self.context_panel_active = True
            self.main_window.show_context_panel()
            self._switch_to_context_view()
        except Exception as e:
            self.main_window.show_error("Context Lookup Failed", f"Could not retrieve word appearances: {e}")
    
    @Slot()
    def _on_context_panel_closed(self):
        """Handle when user closes the context panel."""
        if self.context_coordinator is not None:
            # Let coordinator emit restore request
            self.context_coordinator._on_context_panel_closed()
            return
        self.context_panel_active = False
        self.main_window.hide_context_panel()
        if (
            self.view_mode.name != self.previous_view_mode.name
            or self.current_page_number != self.previous_page_number
        ):
            self.current_page_number = self.previous_page_number
            self.view_mode = self.previous_view_mode
            self._render_current_page()

    def _switch_to_context_view(self):
        """Adjust page and view mode when entering context panel view."""
        current_before_context = self.current_page_number

        target_page = self.view_mode.page_for_context(
            current_page_number=self.current_page_number,
            last_clicked_page_index=self.last_clicked_page_index,
        )
        context_mode = self.view_mode.context_view_mode()

        mode_changed = context_mode.name != self.view_mode.name
        page_changed = target_page != current_before_context

        self.current_page_number = target_page
        if mode_changed:
            self.view_mode = context_mode
        if mode_changed or page_changed:
            self._render_current_page()
    
    @Slot(int, int, int)
    def _on_appearance_selected(self, word_id: int, appearance_id: int, page_index: int):
        """Forward appearance selection to coordinator or handle inline."""
        if self.context_coordinator is not None:
            self.context_coordinator._on_appearance_selected(word_id, appearance_id, page_index)
            return
        if self.current_volume is None:
            return
        if not (0 <= page_index < self.current_volume.total_pages):
            self.main_window.show_error("Invalid Page", f"Page {page_index + 1} is not available in this volume.")
            return
        self.current_page_number = self.view_mode.page_for_appearance(
            self.current_volume, page_index, self.current_page_number
        )
        self._render_current_page()
