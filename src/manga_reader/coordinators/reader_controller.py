"""Reader Controller - Central coordinator for the reading session."""

from pathlib import Path

from PySide6.QtCore import QObject, Slot

from manga_reader.core import MangaVolume
from manga_reader.io import VolumeIngestor
from manga_reader.services import DictionaryService
from manga_reader.ui import MainWindow, MangaCanvas


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
    ):
        super().__init__()
        
        self.main_window = main_window
        self.canvas = canvas
        self.ingestor = ingestor
        self.dictionary_service = dictionary_service
        
        # Session state
        self.current_volume: MangaVolume | None = None
        self.current_page_number: int = 0
        self.view_mode: str = "single"  # "single" or "double"
    
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
    def handle_noun_clicked(self, lemma: str, surface: str, mouse_x: int, mouse_y: int):
        """Handle noun clicks from the canvas and show dictionary popup."""
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
