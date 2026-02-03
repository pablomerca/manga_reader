"""Reader Controller - Central coordinator for the reading session."""

from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Slot

from manga_reader.coordinators.library_coordinator import LibraryCoordinator
from manga_reader.core import MangaVolume
from manga_reader.io import VolumeIngestor
from typing import Optional

from manga_reader.services import VocabularyService
from manga_reader.ui import MainWindow, MangaCanvas, SentenceAnalysisPanel
from .word_interaction_coordinator import WordInteractionCoordinator
from .context_panel_coordinator import ContextPanelCoordinator
from .context_sync_coordinator import ContextSyncCoordinator
from .sentence_analysis_coordinator import SentenceAnalysisCoordinator

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
        sentence_analysis_coordinator: SentenceAnalysisCoordinator,
        sentence_analysis_panel: SentenceAnalysisPanel,
        dictionary_panel_coordinator=None,
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
        if sentence_analysis_coordinator is None:
            raise ValueError("SentenceAnalysisCoordinator must not be None")
        if sentence_analysis_panel is None:
            raise ValueError("SentenceAnalysisPanel must not be None")

        self.word_interaction = word_interaction
        self.context_coordinator = context_coordinator
        self.context_sync_coordinator = context_sync_coordinator
        self.sentence_analysis_coordinator = sentence_analysis_coordinator
        self.dictionary_panel_coordinator = dictionary_panel_coordinator
        self.sentence_panel = sentence_analysis_panel
        
        # Session state
        self.current_volume: MangaVolume | None = None
        self.current_page_number: int = 0
        self.view_mode: ViewMode = SINGLE_PAGE_MODE
        self._sentence_previous_view_mode: ViewMode | None = None
        
        # Timer for delayed highlighting (to allow async rendering)
        self._highlight_timer: Optional[QTimer] = None
        

        # Wire context coordinator requests to handler slots
        self.context_coordinator.navigate_to_page_requested.connect(self._handle_navigate_to_page_request)
        self.context_coordinator.view_mode_change_requested.connect(self._handle_view_mode_change_request)
        self.context_coordinator.restore_view_requested.connect(self._handle_restore_view_request)

        # Wire sentence analysis actions
        self.canvas.block_clicked.connect(self._handle_block_clicked)
        self.sentence_panel.translate_clicked.connect(self.sentence_analysis_coordinator.request_translation)
        self.sentence_panel.explain_clicked.connect(self.sentence_analysis_coordinator.request_explanation)
        self.sentence_panel.close_clicked.connect(self._handle_sentence_panel_closed)
        
        # Wire coordinator signals to panel UI updates
        self.sentence_analysis_coordinator.translation_started.connect(self.sentence_panel.show_translation_loading)
        self.sentence_analysis_coordinator.translation_completed.connect(self.sentence_panel.show_translation_success)
        self.sentence_analysis_coordinator.translation_failed.connect(self.sentence_panel.show_translation_error)
        self.sentence_analysis_coordinator.explanation_loading.connect(self.sentence_panel.show_explanation_loading)
        self.sentence_analysis_coordinator.explanation_completed.connect(self.sentence_panel.show_explanation_success)
        self.sentence_analysis_coordinator.explanation_failed.connect(self.sentence_panel.show_explanation_error)
        self.sentence_analysis_coordinator.block_selected.connect(self.sentence_panel.set_original_text)
        
        # Wire main window return to library signal
        self.main_window.return_to_library_requested.connect(self._handle_return_to_library)
    
    @Slot(Path)
    def handle_volume_opened(
        self,
        volume_path: Path,
        show_success_dialog: bool = True,
        defer_render: bool = False,
        save_previous_progress: bool = True,
        resume_last_page: bool = True,
    ):
        """
        Handle when user selects a volume folder.
        
        Args:
            volume_path: Path to the selected volume directory
            show_success_dialog: Whether to show "Volume Loaded" success dialog (default: True)
            defer_render: Whether to skip initial render (default: False). Used when jumping to
                         a specific page to avoid rendering page 0 first.
            save_previous_progress: Whether to persist the last page of the current volume
                                    before switching (default: True).
            resume_last_page: Whether to resume from the saved last page (default: True).
        """
        if save_previous_progress:
            self._persist_current_progress()

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
        
        # Add to library if we have a coordinator and set volume_id
        if self.library_coordinator:
            try:
                library_volume = self.library_coordinator.add_volume_to_library(volume_path)
                # Set the volume_id from the library so we can track it for multi-volume navigation
                volume.volume_id = library_volume.id
                if resume_last_page:
                    last_page_read = min(
                        library_volume.last_page_read,
                        max(volume.total_pages - 1, 0),
                    )
                    self.current_page_number = last_page_read
            except RuntimeError as e:
                # Log error but don't block reading
                print(f"Warning: Could not add volume to library: {e}")
        
        # Switch to reading view
        self.main_window.display_reading_view(self.canvas)
        
        # Render the first page (unless deferred for later navigation)
        if not defer_render:
            self._render_current_page()
        
        # Show success message only if requested (skip for silent loads)
        if show_success_dialog:
            self.main_window.show_info(
                "Volume Loaded",
                f"Successfully loaded: {volume.title}\n"
                f"Total pages: {volume.total_pages}"
            )

    @Slot()
    def handle_sync_context_requested(self):
        """Trigger synchronization of tracked word appearances for the current volume."""
        self.context_sync_coordinator.synchronize_current_volume()

    def _persist_current_progress(self) -> None:
        """Persist the current volume's last page if possible."""
        if self.current_volume is None or self.library_coordinator is None:
            return
        volume_id = getattr(self.current_volume, "volume_id", None)
        if volume_id is None:
            return
        try:
            self.library_coordinator.update_reading_progress(
                volume_id=volume_id,
                page_index=self.current_page_number,
            )
        except RuntimeError as e:
            print(f"Warning: Could not persist reading progress: {e}")

    @Slot()
    def handle_app_closing(self) -> None:
        """Persist progress when the application is closing."""
        self._persist_current_progress()
    
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
            if self.dictionary_panel_coordinator:
                self.dictionary_panel_coordinator.set_session_context(self.current_volume, self.current_page_number)
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
    def _handle_restore_view_request(self, volume_path: str, mode_name: str, page_number: int):
        """Handle request to restore previous view state including volume."""
        from pathlib import Path
        
        # If we're in a different volume, load the correct one first
        if self.current_volume is None or Path(volume_path).resolve() != self.current_volume.volume_path.resolve():
            try:
                # Load the volume silently (no dialog)
                self.handle_volume_opened(
                    Path(volume_path),
                    show_success_dialog=False,
                    defer_render=True,
                    save_previous_progress=False,
                    resume_last_page=False,
                )
            except Exception as e:
                print(f"Warning: Could not restore volume: {e}")
                # Continue with current volume if restoration fails
        
        # Now restore the view mode and page number
        self.view_mode = create_view_mode(mode_name)
        self.current_page_number = page_number
        self._render_current_page()

    @Slot(int, str, int, dict)
    def handle_navigate_to_appearance(self, volume_id: int, volume_path: str, page_index: int, crop_coords: dict):
        """
        Navigate to a word appearance and highlight its block.
        
        Handles navigation from context panel to specific appearance. This method:
        1. Checks if already in the correct volume (by comparing paths)
        2. If in different volume, loads that volume silently (no dialog)
        3. Jumps to the target page
        4. Delays highlighting to allow page rendering to complete
        5. Highlights the exact block coordinates
        
        Args:
            volume_id: The volume ID where the appearance is located
            volume_path: The path to the volume (used for path comparison and fallback)
            page_index: The page to navigate to (0-indexed)
            crop_coords: Dictionary with x, y, width, height of the block to highlight
        """
        # Resolve the target volume path for comparison
        target_path = Path(volume_path).resolve() if volume_path else None
        
        # Check if we're already in this volume by comparing resolved paths
        already_in_volume = (
            self.current_volume is not None
            and target_path is not None
            and target_path == self.current_volume.volume_path.resolve()
        )
        
        # Only load volume if we're not already in it
        if not already_in_volume:
            # Try to load the target volume
            loaded_successfully = False
            
            # First, try loading by volume_id from library
            if self.library_coordinator:
                try:
                    library_volume = self.library_coordinator.library_repository.get_volume_by_id(volume_id)
                    # Load silently (no "Volume Loaded" dialog) with deferred render for smooth navigation
                    self.handle_volume_opened(
                        library_volume.folder_path,
                        show_success_dialog=False,
                        defer_render=True,
                        save_previous_progress=False,
                        resume_last_page=False,
                    )
                    loaded_successfully = True
                except RuntimeError:
                    # Volume not found by ID, will try fallback below
                    pass
            
            # Fallback: if volume not found by ID in library, try using the volume path
            if not loaded_successfully and volume_path:
                try:
                    self.handle_volume_opened(
                        Path(volume_path),
                        show_success_dialog=False,
                        defer_render=True,
                        save_previous_progress=False,
                        resume_last_page=False,
                    )
                    loaded_successfully = True
                except Exception as e:
                    # If fallback also fails, show error and return
                    self.main_window.show_error(
                        "Volume Not Found",
                        f"Could not find the volume for this appearance.\n"
                        f"Path: {volume_path}\nError: {e}"
                    )
                    return
            
            if not loaded_successfully:
                # No fallback path available
                self.main_window.show_error(
                    "Volume Not Found",
                    f"Could not find the volume for this appearance (ID: {volume_id})."
                )
                return
        
        # Jump to the target page and render (first render for deferred loads)
        # This ensures we only render the target page, never page 0
        if self.current_volume is not None:
            if 0 <= page_index < self.current_volume.total_pages:
                self.current_page_number = page_index
                self._render_current_page()
        
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
        self._persist_current_progress()
        if self.library_coordinator:
            self.library_coordinator.show_library()

    @Slot(int, int)
    def _handle_block_clicked(self, block_id: int, page_index: int):
        """Handle block click from canvas and open sentence analysis panel."""
        if self.current_volume is None:
            raise RuntimeError("No volume loaded in session")

        # Normalize page index (handle -1 as current page)
        clicked_page = page_index if page_index >= 0 else self.current_page_number
        
        if not (0 <= clicked_page < self.current_volume.total_pages):
            self.main_window.show_error(
                "Invalid selection",
                f"Page index {clicked_page} is out of range.",
            )
            return

        page = self.current_volume.get_page(clicked_page)
        if block_id < 0 or block_id >= len(page.ocr_blocks):
            self.main_window.show_error(
                "Invalid selection",
                "Selected block is out of range for this page.",
            )
            return

        block = page.ocr_blocks[block_id]
        text = block.full_text
        volume_id = str(self.current_volume.volume_path)

        # Determine if we need to re-render the page
        need_render = False
        
        # Force single page while sentence panel is open; remember previous mode
        if self.view_mode.name == "double":
            self._sentence_previous_view_mode = self.view_mode
            self.view_mode = create_view_mode("single")
            # Use page_for_context logic to compute the correct page to display
            target_page = self.view_mode.page_for_context(
                current_page_number=self.current_page_number,
                last_clicked_page_index=clicked_page,
            )
            # Only render if we're changing pages or switching from double mode
            if target_page != self.current_page_number or self._sentence_previous_view_mode is not None:
                self.current_page_number = target_page
                need_render = True
        else:
            # Already in single-page mode, only render if changing pages
            if clicked_page != self.current_page_number:
                self.current_page_number = clicked_page
                need_render = True
        
        # Only render if we need to (preserves zoom level when clicking blocks on same page)
        if need_render:
            self._render_current_page()

        self.sentence_panel.set_original_text(text)
        self.main_window.show_sentence_panel()
        self.sentence_analysis_coordinator.on_block_selected(text, volume_id)

    @Slot()
    def _handle_sentence_panel_closed(self):
        """Handle sentence panel close action."""
        self.sentence_analysis_coordinator.on_panel_closed()
        self.sentence_panel.clear()
        self.main_window.hide_sentence_panel()
        if self._sentence_previous_view_mode is not None:
            self.view_mode = self._sentence_previous_view_mode
            self._sentence_previous_view_mode = None
            self._render_current_page()
