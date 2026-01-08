"""Reader Controller - Central coordinator for the reading session."""

from pathlib import Path

from PySide6.QtCore import QObject, Slot

from manga_reader.core import MangaVolume
from manga_reader.io import VolumeIngestor
from manga_reader.services import DictionaryService, VocabularyService
from manga_reader.ui import MainWindow, MangaCanvas, WordContextPanel


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
    ):
        super().__init__()
        
        self.main_window = main_window
        self.canvas = canvas
        self.ingestor = ingestor
        self.dictionary_service = dictionary_service
        self.vocabulary_service = vocabulary_service
        self.context_panel = context_panel
        
        # Session state
        self.current_volume: MangaVolume | None = None
        self.current_page_number: int = 0
        self.view_mode: str = "single"  # "single" or "double"
        self.previous_view_mode: str = "single"  # For restoring when context closes
        self.context_panel_active: bool = False  # Track if context panel is open
        
        # Wire context panel signals
        self.context_panel.closed.connect(self._on_context_panel_closed)
        self.context_panel.appearance_selected.connect(self._on_appearance_selected)
    
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
        
        pages_to_render = self._get_pages_to_render()
        if pages_to_render:
            self.canvas.render_pages(pages_to_render)
        else:
            self.canvas.hide_dictionary_popup()
    
    def _get_pages_to_render(self) -> list:
        """
        Determine which page(s) to render based on view mode and page orientation.
        
        Returns:
            List of MangaPage objects to render
        """
        if self.current_volume is None:
            return []
        
        current_page = self.current_volume.get_page(self.current_page_number)
        if not current_page:
            return []
        
        # Single page mode: always return one page
        if self.view_mode == "single":
            return [current_page]
        
        # Double page mode
        # If current page is landscape, show only this page
        if not current_page.is_portrait():
            return [current_page]
        
        # Check if there's a next page
        if self.current_page_number >= self.current_volume.total_pages - 1:
            # Last page, show only current
            return [current_page]
        
        next_page = self.current_volume.get_page(self.current_page_number + 1)
        if not next_page:
            return [current_page]
        
        # If next page is also portrait, show both
        if next_page.is_portrait():
            return [current_page, next_page]
        
        # Next page is landscape, show only current
        return [current_page]
    
    def next_page(self):
        """Navigate to the next page, skipping appropriately in double page mode."""
        if self.current_volume is None:
            return
        
        # Determine how many pages to skip
        pages_displayed = len(self._get_pages_to_render())
        next_page_num = self.current_page_number + pages_displayed
        
        if next_page_num < self.current_volume.total_pages:
            self.current_page_number = next_page_num
            self._render_current_page()
    
    def previous_page(self):
        """Navigate to the previous page, accounting for double page mode."""
        if self.current_volume is None:
            return
        
        if self.current_page_number > 0:
            # In double page mode, we need to check if the previous spread was double
            if self.view_mode == "double" and self.current_page_number >= 2:
                # Check the page before current
                prev_page = self.current_volume.get_page(self.current_page_number - 2)
                current_prev = self.current_volume.get_page(self.current_page_number - 1)
                
                # If both are portrait, we were showing a double spread, go back 2
                if prev_page and current_prev and prev_page.is_portrait() and current_prev.is_portrait():
                    self.current_page_number -= 2
                else:
                    self.current_page_number -= 1
            else:
                self.current_page_number -= 1
            
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
        if mode not in ("single", "double"):
            return
        
        self.view_mode = mode
        # Re-render current page(s) with new mode
        self._render_current_page()

    @Slot(str, str, int, int)
    def handle_word_clicked(self, lemma: str, surface: str, mouse_x: int, mouse_y: int):
        """Handle word clicks from the canvas and show dictionary popup."""
        if self.dictionary_service is None:
            return

        entry = self.dictionary_service.lookup(lemma, surface)

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
        }

        self.canvas.show_dictionary_popup(payload)

    @Slot(str, str, str)
    def handle_track_word(self, lemma: str, reading: str, part_of_speech: str):
        """
        Handle tracking a word from the dictionary popup.
        
        Args:
            lemma: The dictionary base form
            reading: The kana reading
            part_of_speech: POS tag (e.g., "Noun", "Verb")
        """
        if self.current_volume is None:
            self.main_window.show_error(
                "No Volume Open",
                "Please open a manga volume before tracking words."
            )
            return

        current_page = self.current_volume.get_page(self.current_page_number)
        if not current_page:
            return

        # For MVP, use placeholder coordinates and sentence
        # TODO: Get actual block coordinates and sentence from canvas selection
        crop_coords = {"x": 0, "y": 0, "width": 100, "height": 50}
        sentence = current_page.get_all_text()[:100]  # First 100 chars as context

        try:
            word, appearance = self.vocabulary_service.track_word(
                lemma=lemma,
                reading=reading,
                part_of_speech=part_of_speech,
                volume_path=self.current_volume.volume_path,
                page_index=self.current_page_number,
                crop_coordinates=crop_coords,
                sentence_text=sentence,
            )
            
            self.main_window.show_info(
                "Word Tracked",
                f"Added '{lemma}' to your vocabulary!\n"
                f"Reading: {reading}\n"
                f"Type: {part_of_speech}"
            )
        except Exception as e:
            self.main_window.show_error(
                "Tracking Failed",
                f"Could not track word: {e}"
            )

    @Slot()
    def handle_open_vocabulary_list(self):
        """Handle request to open the vocabulary manager window."""
        try:
            tracked_words = self.vocabulary_service.list_tracked_words()
            
            # For MVP, show simple message with count
            # TODO: Create proper VocabularyManager dialog
            if not tracked_words:
                self.main_window.show_info(
                    "Vocabulary List",
                    "You haven't tracked any words yet.\n\n"
                    "Click on a word in the manga and use the 'Track' button."
                )
            else:
                word_list = "\n".join(
                    f"• {w.lemma} ({w.reading}) - {w.part_of_speech}"
                    for w in tracked_words[:10]
                )
                more_text = f"\n... and {len(tracked_words) - 10} more" if len(tracked_words) > 10 else ""
                
                self.main_window.show_info(
                    "Vocabulary List",
                    f"You have tracked {len(tracked_words)} word(s):\n\n{word_list}{more_text}"
                )
        except Exception as e:
            self.main_window.show_error(
                "List Failed",
                f"Could not retrieve vocabulary list: {e}"
            )

    @Slot(int)
    def handle_view_word_context(self, word_id: int):
        """
        Handle request to view all appearances of a tracked word.
        Opens the context split view panel showing all occurrences.
        
        Args:
            word_id: The ID of the tracked word
        """
        try:
            # Retrieve the tracked word and its appearances
            tracked_words = self.vocabulary_service.list_tracked_words()
            tracked_word = next((w for w in tracked_words if w.id == word_id), None)
            
            if not tracked_word:
                self.main_window.show_error(
                    "Word Not Found",
                    "The requested word could not be found in vocabulary."
                )
                return
            
            appearances = self.vocabulary_service.list_appearances(word_id)
            
            if not appearances:
                self.main_window.show_info(
                    "No Appearances",
                    f"The word '{tracked_word.lemma}' has no recorded appearances."
                )
                return
            
            # Display word context in split view panel
            self.context_panel.display_word_context(
                word_id=word_id,
                word_lemma=tracked_word.lemma,
                appearances=appearances
            )
            
            # Save current view mode and switch to single page for context panel
            self.previous_view_mode = self.view_mode
            self.context_panel_active = True
            
            # Show the context panel
            self.main_window.show_context_panel()
            
            # Switch to single page mode if in double page mode
            if self.view_mode == "double":
                self.view_mode = "single"
                self._render_current_page()
                
        except Exception as e:
            self.main_window.show_error(
                "Context Lookup Failed",
                f"Could not retrieve word appearances: {e}"
            )
    
    @Slot()
    def _on_context_panel_closed(self):
        """Handle when user closes the context panel."""
        self.context_panel_active = False
        self.main_window.hide_context_panel()
        
        # Restore previous view mode if it was different
        if self.view_mode != self.previous_view_mode:
            self.view_mode = self.previous_view_mode
            self._render_current_page()
    
    @Slot(int, int, int)
    def _on_appearance_selected(self, word_id: int, appearance_id: int, page_index: int):
        """
        Handle when user selects an appearance in the context panel.
        Navigate to that page.
        
        Args:
            word_id: The word ID (for future use)
            appearance_id: The appearance ID (for future use - could show highlight)
            page_index: The page to jump to (0-indexed)
        """
        if self.current_volume is None:
            return
        
        # Validate page index
        if 0 <= page_index < self.current_volume.total_pages:
            self.current_page_number = page_index
            self._render_current_page()
        else:
            self.main_window.show_error(
                "Invalid Page",
                f"Page {page_index + 1} is not available in this volume."
            )
