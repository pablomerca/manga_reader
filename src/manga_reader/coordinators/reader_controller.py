"""Reader Controller - Central coordinator for the reading session."""

from pathlib import Path
from PySide6.QtCore import QObject, Slot

from manga_reader.core import MangaVolume
from manga_reader.io import VolumeIngestor
from manga_reader.ui import MainWindow, MangaCanvas


class ReaderController(QObject):
    """
    Central Nervous System of the application.
    Manages live session state and routes signals between UI and services.
    """
    
    def __init__(self, main_window: MainWindow, canvas: MangaCanvas, ingestor: VolumeIngestor):
        super().__init__()
        
        self.main_window = main_window
        self.canvas = canvas
        self.ingestor = ingestor
        
        # Session state
        self.current_volume: MangaVolume | None = None
        self.current_page_number: int = 0
    
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
        """Render the current page to the canvas."""
        if self.current_volume is None:
            return
        
        page = self.current_volume.get_page(self.current_page_number)
        if page:
            self.canvas.render_page(page)
    
    def next_page(self):
        """Navigate to the next page."""
        if self.current_volume is None:
            return
        
        if self.current_page_number < self.current_volume.total_pages - 1:
            self.current_page_number += 1
            self._render_current_page()
    
    def previous_page(self):
        """Navigate to the previous page."""
        if self.current_volume is None:
            return
        
        if self.current_page_number > 0:
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
