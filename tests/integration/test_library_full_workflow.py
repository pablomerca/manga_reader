#!/usr/bin/env python3
"""
Integration tests for Library Screen - Full workflow validation.

Tests the complete user journey through library functionality:
1. Open application → see library
2. Open volume → added to library
3. Return to library → volume displayed
4. Click volume → opens for reading
5. Delete volume → removed from library
6. Edit title → persists to database
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from PySide6.QtWidgets import QApplication

from manga_reader.coordinators import LibraryCoordinator
from manga_reader.core import MangaPage, MangaVolume, OCRBlock
from manga_reader.io import LibraryRepository
from manga_reader.services import ThumbnailService
from manga_reader.ui import LibraryScreen


def ensure_qt_app():
    if QApplication.instance() is None:
        QApplication([])


@pytest.fixture
def temp_db():
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def db_connection(temp_db):
    """Create a database connection with schema."""
    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Initialize library schema
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS library_volumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            folder_path TEXT NOT NULL UNIQUE,
            cover_image_path TEXT,
            date_added INTEGER NOT NULL,
            last_opened INTEGER NOT NULL
        );
        """
    )
    conn.commit()
    
    yield conn
    conn.close()


@pytest.fixture
def library_repo(db_connection):
    """Create a LibraryRepository."""
    return LibraryRepository(db_connection)


@pytest.fixture
def mock_volume(tmp_path):
    """Create a mock MangaVolume with valid structure.
    
    Uses tmp_path (function-scoped) for complete isolation.
    Avoids any class-level property mocking that affects other tests.
    """
    # Create volume folder with .mokuro file
    volume_path = tmp_path / "test_volume"
    volume_path.mkdir()
    (volume_path / "test_volume.mokuro").touch()
    
    # Create first page image
    image_path = volume_path / "page001.jpg"
    image_path.touch()
    
    # Create mock MangaPage with OCR blocks for realism
    page = MangaPage(
        page_number=0,
        image_path=image_path,
        width=800,
        height=1200,
        ocr_blocks=[],  # Empty is fine for mocking
    )
    
    # Create MangaVolume and add page via public API
    volume = MangaVolume(title="Test Volume", volume_path=volume_path)
    volume.add_page(page)
    
    return volume, volume_path


def test_full_workflow_add_open_delete_volume(library_repo, mock_volume, tmp_path):
    """Integration test: Add volume → open → delete workflow."""
    ensure_qt_app()
    
    volume, volume_path = mock_volume
    
    # Setup mocks
    mock_ingestor = MagicMock()
    mock_ingestor.ingest_volume.return_value = volume
    
    mock_thumbnail_service = MagicMock()
    cover_path = tmp_path / "cover.jpg"
    cover_path.touch()
    mock_thumbnail_service.generate_thumbnail.return_value = cover_path
    
    mock_main_window = MagicMock()
    mock_main_window.volume_opened = MagicMock()
    mock_main_window.volume_opened.emit = MagicMock()
    
    library_screen = LibraryScreen()
    
    coordinator = LibraryCoordinator(
        library_screen=library_screen,
        library_repository=library_repo,
        volume_ingestor=mock_ingestor,
        thumbnail_service=mock_thumbnail_service,
        main_window=mock_main_window,
    )
    
    # Step 1: Add volume to library
    lib_volume = coordinator.add_volume_to_library(volume_path, "Test Volume")
    assert lib_volume.title == "Test Volume"
    assert lib_volume.folder_path == volume_path.resolve()
    
    # Step 2: Verify volume is in database
    volumes = library_repo.get_all_volumes()
    assert len(volumes) == 1
    assert volumes[0].title == "Test Volume"
    
    # Step 3: Open volume (simulate clicking in library)
    import time
    time.sleep(0.05)  # Ensure timestamp difference
    coordinator.handle_volume_selected(volume_path)
    mock_main_window.volume_opened.emit.assert_called_once_with(volume_path)
    
    # Step 4: Verify last_opened was updated
    updated_volume = library_repo.get_volume_by_path(volume_path)
    assert updated_volume.last_opened >= lib_volume.last_opened
    
    # Step 5: Delete volume from library
    coordinator.handle_volume_deleted(volume_path)
    
    # Step 6: Verify volume is gone
    volumes_after_delete = library_repo.get_all_volumes()
    assert len(volumes_after_delete) == 0


def test_workflow_title_editing_persists(library_repo, mock_volume, tmp_path):
    """Integration test: Title editing persists to database."""
    ensure_qt_app()
    
    volume, volume_path = mock_volume
    
    # Setup
    mock_ingestor = MagicMock()
    mock_ingestor.ingest_volume.return_value = volume
    
    mock_thumbnail_service = MagicMock()
    cover_path = tmp_path / "cover.jpg"
    cover_path.touch()
    mock_thumbnail_service.generate_thumbnail.return_value = cover_path
    
    coordinator = LibraryCoordinator(
        library_screen=LibraryScreen(),
        library_repository=library_repo,
        volume_ingestor=mock_ingestor,
        thumbnail_service=mock_thumbnail_service,
        main_window=MagicMock(),
    )
    
    # Add volume
    coordinator.add_volume_to_library(volume_path, "Original Title")
    
    # Edit title
    new_title = "Updated Title"
    coordinator.handle_title_changed(volume_path, new_title)
    
    # Verify title persisted
    volume_after_edit = library_repo.get_volume_by_path(volume_path)
    assert volume_after_edit.title == new_title


def test_workflow_relocation_updates_path(library_repo, tmp_path):
    """Integration test: Volume relocation updates database path."""
    ensure_qt_app()
    
    # Create initial volume location
    old_path = tmp_path / "old_location"
    old_path.mkdir()
    (old_path / "volume.mokuro").touch()
    
    # Create new location with .mokuro file
    new_path = tmp_path / "new_location"
    new_path.mkdir()
    (new_path / "volume.mokuro").touch()
    
    # Add volume with old path
    cover_path = tmp_path / "cover.jpg"
    cover_path.touch()
    library_repo.add_volume("Test Volume", old_path, cover_path)
    
    # Setup mocks
    mock_main_window = MagicMock()
    mock_main_window.show_relocation_dialog.return_value = new_path
    mock_main_window.volume_opened = MagicMock()
    mock_main_window.volume_opened.emit = MagicMock()
    
    coordinator = LibraryCoordinator(
        library_screen=LibraryScreen(),
        library_repository=library_repo,
        volume_ingestor=MagicMock(),
        thumbnail_service=MagicMock(),
        main_window=mock_main_window,
    )
    
    # Simulate clicking on volume with old (removed) path
    # Remove .mokuro file first, then directory
    (old_path / "volume.mokuro").unlink()
    old_path.rmdir()  # Remove empty directory to trigger relocation
    
    coordinator.handle_volume_selected(old_path)
    
    # Verify relocation dialog was shown
    mock_main_window.show_relocation_dialog.assert_called_once()
    
    # Verify database was updated
    try:
        library_repo.get_volume_by_path(old_path)
        assert False, "Old path should not exist"
    except RuntimeError:
        pass  # Expected
    
    updated_volume = library_repo.get_volume_by_path(new_path)
    assert updated_volume.title == "Test Volume"
    assert updated_volume.folder_path == new_path.resolve()


def test_workflow_multiple_volumes_ordering(library_repo, mock_volume, tmp_path):
    """Integration test: Multiple volumes ordered by last_opened."""
    ensure_qt_app()
    
    volume, volume_path1 = mock_volume
    
    # Create second volume
    volume_path2 = tmp_path / "volume2"
    volume_path2.mkdir()
    (volume_path2 / "volume2.mokuro").touch()
    
    # Add thumbnails
    cover1 = tmp_path / "cover1.jpg"
    cover2 = tmp_path / "cover2.jpg"
    cover1.touch()
    cover2.touch()
    
    # Add volumes with different timestamps
    import time
    vol1 = library_repo.add_volume("Volume 1", volume_path1, cover1)
    time.sleep(0.05)  # Ensure different timestamps
    vol2 = library_repo.add_volume("Volume 2", volume_path2, cover2)
    
    # Get all volumes (should be ordered by last_opened DESC)
    volumes = library_repo.get_all_volumes()
    assert len(volumes) == 2
    # Verify most recent is first (may be Vol1 or Vol2 depending on timing)
    assert volumes[0].last_opened >= volumes[1].last_opened
    
    # Update last_opened for volume 1
    time.sleep(0.05)
    library_repo.update_last_opened(volume_path1)
    
    # Verify ordering changed - volume 1 should now be first
    volumes_after_update = library_repo.get_all_volumes()
    assert volumes_after_update[0].folder_path == volume_path1.resolve()  # Now most recent


def test_workflow_library_survives_restart(library_repo, temp_db, mock_volume, tmp_path):
    """Integration test: Library persists across application restarts."""
    ensure_qt_app()
    
    volume, volume_path = mock_volume
    
    # Session 1: Add volume
    cover_path = tmp_path / "cover.jpg"
    cover_path.touch()
    vol1 = library_repo.add_volume("Persistent Volume", volume_path, cover_path)
    original_id = vol1.id
    
    # Close connection (simulate app shutdown)
    library_repo.connection.close()
    
    # Session 2: Reopen database (simulate app restart)
    conn2 = sqlite3.connect(str(temp_db))
    conn2.row_factory = sqlite3.Row
    repo2 = LibraryRepository(conn2)
    
    # Verify volume still exists
    volumes = repo2.get_all_volumes()
    assert len(volumes) == 1
    assert volumes[0].id == original_id
    assert volumes[0].title == "Persistent Volume"
    assert volumes[0].folder_path == volume_path.resolve()
    
    conn2.close()
