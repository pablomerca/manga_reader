"""Library Coordinator - Orchestrates library volume management and display."""

from pathlib import Path
from typing import List

from PySide6.QtCore import QObject, Slot

from manga_reader.core import LibraryVolume
from manga_reader.io import LibraryRepository, VolumeIngestor
from manga_reader.services import ThumbnailService
from manga_reader.ui import LibraryScreen, MainWindow


class LibraryCoordinator(QObject):
    """Manages library screen display and volume operations.
    
    Responsibilities:
    - Display library screen on startup
    - Load volumes from repository
    - Handle volume selection (open for reading)
    - Handle volume deletion (with confirmation)
    - Handle title editing
    - Generate thumbnails when volumes are added
    - Switch between library and reading views
    """

    def __init__(
        self,
        library_screen: LibraryScreen,
        library_repository: LibraryRepository,
        volume_ingestor: VolumeIngestor,
        thumbnail_service: ThumbnailService,
        main_window: MainWindow,
    ):
        super().__init__()
        
        if library_screen is None:
            raise ValueError("LibraryScreen must not be None")
        if library_repository is None:
            raise ValueError("LibraryRepository must not be None")
        if volume_ingestor is None:
            raise ValueError("VolumeIngestor must not be None")
        if thumbnail_service is None:
            raise ValueError("ThumbnailService must not be None")
        if main_window is None:
            raise ValueError("MainWindow must not be None")
        
        self.library_screen = library_screen
        self.library_repository = library_repository
        self.volume_ingestor = volume_ingestor
        self.thumbnail_service = thumbnail_service
        self.main_window = main_window
        
        # Wire library screen signals
        self.library_screen.volume_selected.connect(self.handle_volume_selected)
        self.library_screen.volume_deleted.connect(self.handle_volume_deleted)
        self.library_screen.volume_title_changed.connect(self.handle_title_changed)
    
    def show_library(self):
        """Display the library screen and reload volumes."""
        self._load_and_display_volumes()
        self.main_window.display_library_view(self.library_screen)
    
    def add_volume_to_library(self, volume_path: Path, title: str = "") -> LibraryVolume:
        """Add or update a volume in the library.
        
        Args:
            volume_path: Absolute path to the volume folder.
            title: Custom title (defaults to folder name if empty).
            
        Returns:
            LibraryVolume: The added/updated volume.
            
        Raises:
            RuntimeError: If volume addition fails.
        """
        volume_path = Path(volume_path).resolve()
        
        # Use folder name as default title
        volume_title = title or volume_path.name
        
        # Load the volume to get the first page image
        volume = self.volume_ingestor.ingest_volume(volume_path)
        if volume is None:
            raise RuntimeError(f"Failed to ingest volume: {volume_path}")
        
        if volume.total_pages == 0:
            raise RuntimeError(f"Volume has no pages: {volume_path}")
        
        # Generate thumbnail from first page
        first_page = volume.get_page(0)
        if first_page is None or first_page.image_path is None:
            raise RuntimeError(f"Cannot access first page image: {volume_path}")
        
        try:
            cover_path = self.thumbnail_service.generate_thumbnail(
                first_page_image=first_page.image_path,
                volume_folder_path=volume_path,
            )
        except RuntimeError as e:
            raise RuntimeError(f"Failed to generate thumbnail: {e}") from e
        
        # Add to repository
        lib_volume = self.library_repository.add_volume(
            title=volume_title,
            folder_path=volume_path,
            cover_image_path=cover_path,
        )
        
        return lib_volume
    
    @Slot(Path)
    def handle_volume_selected(self, folder_path: Path):
        """Handle when user selects a volume from the library.
        
        Args:
            folder_path: Path to the selected volume.
        """
        # Update last_opened timestamp
        try:
            self.library_repository.update_last_opened(folder_path)
        except RuntimeError:
            # Volume may have been deleted; continue anyway
            pass
        
        # Emit signal to open the volume in reader
        self.main_window.volume_opened.emit(folder_path)
    
    @Slot(Path)
    def handle_volume_deleted(self, folder_path: Path):
        """Handle when user deletes a volume from the library.
        
        Args:
            folder_path: Path to the volume to delete.
        """
        try:
            self.library_repository.delete_volume(folder_path)
        except RuntimeError as e:
            self.main_window.show_error("Delete Error", str(e))
            return
        
        # Reload and display updated library
        self._load_and_display_volumes()
    
    @Slot(Path, str)
    def handle_title_changed(self, folder_path: Path, new_title: str):
        """Handle when user edits a volume title.
        
        Args:
            folder_path: Path to the volume.
            new_title: New title text.
        """
        try:
            self.library_repository.update_title(folder_path, new_title)
        except RuntimeError as e:
            self.main_window.show_error("Title Update Error", str(e))
    
    def _load_and_display_volumes(self):
        """Load all volumes from repository and display in library screen."""
        try:
            volumes = self.library_repository.get_all_volumes()
            self.library_screen.display_volumes(volumes)
        except RuntimeError as e:
            self.main_window.show_error("Library Load Error", str(e))
