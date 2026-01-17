"""Reader Controller - Central coordinator for the reading session."""

from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Slot

from manga_reader.coordinators.library_coordinator import LibraryCoordinator
from manga_reader.core import MangaVolume
from manga_reader.io import VolumeIngestor
from typing import Optional

from manga_reader.services import VocabularyService
from manga_reader.ui import MainWindow, MangaCanvas
from .word_interaction_coordinator import WordInteractionCoordinator
from .context_panel_coordinator import ContextPanelCoordinator
from .context_sync_coordinator import ContextSyncCoordinator

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
        word_interaction: WordInteractionCoordinator,
        context_coordinator: ContextPanelCoordinator,
        context_sync_coordinator: ContextSyncCoordinator,
        vocabulary_service: VocabularyService,
        library_coordinator: LibraryCoordinator,
    ):
        super().__init__()
        
        self.main_window = main_window
        self.canvas = canvas
        self.ingestor = ingestor
        self.vocabulary_service = vocabulary_service
        self.library_coordinator = library_coordinator
        # Fail fast if essential collaborators are missing
        if word_interaction is None:
            raise ValueError("WordInteractionCoordinator must not be None")
        if context_coordinator is None:
            raise ValueError("ContextPanelCoordinator must not be None")
        if context_sync_coordinator is None:
            raise ValueError("ContextSyncCoordinator must not be None")
        if vocabulary_service is None:
            raise ValueError("VocabularyService must not be None")
        if library_coordinator is None:
            raise ValueError("LibraryCoordinator must not be None")

        self.word_interaction = word_interaction
        self.context_coordinator = context_coordinator
        self.context_sync_coordinator = context_sync_coordinator
        
        # Session state
        self.current_volume: MangaVolume | None = None
        self.current_page_number: int = 0
        self.view_mode: ViewMode = SINGLE_PAGE_MODE
        
        # Timer for delayed highlighting (to allow async rendering)
        self._highlight_timer: Optional[QTimer] = None
        

        # Wire context coordinator requests to handler slots
        self.context_coordinator.navigate_to_page_requested.connect(self._handle_navigate_to_page_request)
        self.context_coordinator.view_mode_change_requested.connect(self._handle_view_mode_change_request)
        self.context_coordinator.restore_view_requested.connect(self._handle_restore_view_request)
        
        # Wire main window return to library signal
        self.main_window.return_to_library_requested.connect(self._handle_return_to_library)
    
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

        # Keep context sync coordinator aligned with the active volume
        self.context_sync_coordinator.set_volume(volume)
        
        # Add to library if we have a coordinator
        if self.library_coordinator:
            try:
                self.library_coordinator.add_volume_to_library(volume_path)
            except RuntimeError as e:
                # Log error but don't block reading
                print(f"Warning: Could not add volume to library: {e}")
        
        # Switch to reading view
        self.main_window.display_reading_view(self.canvas)
        
        # Render the first page
        self._render_current_page()
        
        # Show success message
        self.main_window.show_info(
            "Volume Loaded",
            f"Successfully loaded: {volume.title}\n"
            f"Total pages: {volume.total_pages}"
        )

    @Slot()
    def handle_sync_context_requested(self):
        """Trigger synchronization of tracked word appearances for the current volume."""
        self.context_sync_coordinator.synchronize_current_volume()
    
    def _render_current_page(self):
        """Render the current page(s) to the canvas based on view mode."""
        if self.current_volume is None:
            return
        
        pages_to_render = self.view_mode.pages_to_render(
            self.current_volume,
            self.current_page_number,
        )
        if pages_to_render:
            # Fetch tracked lemmas for visual indicators
            tracked_lemmas = self.vocabulary_service.get_all_tracked_lemmas()
            self.canvas.render_pages(pages_to_render, tracked_lemmas=tracked_lemmas)
            # Keep coordinators in sync with current session context
            self.word_interaction.set_volume_context(self.current_volume, self.current_page_number)
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
        self.word_interaction.handle_word_clicked(
            lemma, surface, mouse_x, mouse_y, page_index, block_id
        )

    @Slot(str, str, str)
    def handle_track_word(self, lemma: str, reading: str, part_of_speech: str):
        """Delegate track word handling to WordInteractionCoordinator."""
        # Ensure coordinator has up-to-date session context
        self.word_interaction.set_volume_context(self.current_volume, self.current_page_number)
        self.word_interaction.handle_track_word(lemma, reading, part_of_speech)
    
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
        # Will raise if invalid, surfacing programming errors early
        self.view_mode = create_view_mode(mode)
        self._render_current_page()

    # Slots to handle requests from ContextPanelCoordinator
    @Slot(int)
    def _handle_navigate_to_page_request(self, page_index: int):
        """Handle navigation request from ContextPanelCoordinator."""
        self.jump_to_page(page_index)

    @Slot(str, int)
    def _handle_view_mode_change_request(self, mode_name: str, target_page: int):
        """Handle view mode change request from ContextPanelCoordinator."""
        self.view_mode = create_view_mode(mode_name)
        self.current_page_number = target_page
        self._render_current_page()

    @Slot(str, int)
    def _handle_restore_view_request(self, mode_name: str, page_number: int):
        """Handle request to restore previous view state."""
        self.view_mode = create_view_mode(mode_name)
        self.current_page_number = page_number
        self._render_current_page()

    @Slot(int, int, dict)
    def handle_navigate_to_appearance(self, volume_id: int, page_index: int, crop_coords: dict):
        """
        Navigate to a word appearance and highlight its block.
        
        Handles navigation from context panel to specific appearance. This method:
        1. Jumps to the target page
        2. Delays highlighting to allow page rendering to complete
        3. Highlights the exact block coordinates
        
        Args:
            volume_id: The volume ID (for validation, not currently used)
            page_index: The page to navigate to (0-indexed)
            crop_coords: Dictionary with x, y, width, height of the block to highlight
        """
        # Return early if no volume loaded
        if self.current_volume is None:
            return
        
        # Jump to the target page
        self.jump_to_page(page_index)
        
        # Delay highlighting to allow page rendering (async JavaScript) to complete
        # Use a single-shot timer with 100ms delay to ensure canvas is rendered
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(
            lambda: self.canvas.highlight_block_at_coordinates(crop_coords)
        )
        # Keep timer alive by storing reference (otherwise it gets garbage collected)
        self._highlight_timer = timer
        timer.start(100)  # 100ms delay for page rendering


    # Word interaction is delegated to WordInteractionCoordinator

    @Slot(str)
    def handle_view_context_by_lemma(self, lemma: str):
        """Delegate to ContextPanelCoordinator if available."""
        self.context_coordinator.handle_view_context_by_lemma(lemma)

    @Slot()
    def handle_open_vocabulary_list(self):
        """Delegate to ContextPanelCoordinator if available."""
        self.context_coordinator.handle_open_vocabulary_list()

    # TODO: make more efficient
    @Slot(int)
    def handle_view_word_context(self, word_id: int):
        """Delegate to ContextPanelCoordinator if available."""
        self.context_coordinator.handle_view_word_context(word_id)
    
    @Slot()
    def _on_context_panel_closed(self):
        """Handle when user closes the context panel by delegating to coordinator."""
        self.context_coordinator._on_context_panel_closed()

    
    @Slot(int, int, int)
    def _on_appearance_selected(self, word_id: int, appearance_id: int, page_index: int):
        """Forward appearance selection to coordinator."""
        self.context_coordinator._on_appearance_selected(word_id, appearance_id, page_index)
    
    @Slot()
    def _handle_return_to_library(self):
        """Handle Ctrl+L to return to library."""
        if self.library_coordinator:
            self.library_coordinator.show_library()
