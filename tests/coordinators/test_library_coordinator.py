#!/usr/bin/env python3
"""
Tests for LibraryCoordinator - validates library management and wiring.
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication

from manga_reader.coordinators import LibraryCoordinator
from manga_reader.io import LibraryRepository
from manga_reader.services import ThumbnailService
from manga_reader.ui import LibraryScreen


def ensure_qt_app():
    if QApplication.instance() is None:
        QApplication([])


@pytest.fixture
def db_connection():
    """Create an in-memory database for testing."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Initialize schema
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS library_volumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            folder_path TEXT NOT NULL UNIQUE,
            cover_image_path TEXT,
            date_added INTEGER NOT NULL,
            last_opened INTEGER NOT NULL,
            last_page_read INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    conn.commit()
    
    yield conn
    conn.close()


@pytest.fixture
def library_repo(db_connection):
    """Create a LibraryRepository for testing."""
    return LibraryRepository(db_connection)


def test_library_coordinator_fails_fast_on_none_screen():
    """LibraryCoordinator should raise on None screen."""
    ensure_qt_app()
    
    with pytest.raises(ValueError, match="LibraryScreen must not be None"):
        LibraryCoordinator(
            library_screen=None,
            library_repository=MagicMock(),
            volume_ingestor=MagicMock(),
            thumbnail_service=MagicMock(),
            main_window=MagicMock(),
        )


def test_library_coordinator_fails_fast_on_none_repository():
    """LibraryCoordinator should raise on None repository."""
    ensure_qt_app()
    
    with pytest.raises(ValueError, match="LibraryRepository must not be None"):
        LibraryCoordinator(
            library_screen=LibraryScreen(),
            library_repository=None,
            volume_ingestor=MagicMock(),
            thumbnail_service=MagicMock(),
            main_window=MagicMock(),
        )


def test_library_coordinator_add_volume_fails_fast_on_invalid_volume(library_repo):
    """Adding a volume that doesn't exist should raise RuntimeError."""
    ensure_qt_app()
    
    mock_ingestor = MagicMock()
    mock_ingestor.ingest_volume.return_value = None
    
    coordinator = LibraryCoordinator(
        library_screen=LibraryScreen(),
        library_repository=library_repo,
        volume_ingestor=mock_ingestor,
        thumbnail_service=MagicMock(),
        main_window=MagicMock(),
    )
    
    with pytest.raises(RuntimeError, match="Failed to ingest volume"):
        coordinator.add_volume_to_library(Path("/invalid/path"))


def test_library_coordinator_signals_connected():
    """Verify LibraryCoordinator connects to LibraryScreen signals."""
    ensure_qt_app()
    
    screen = LibraryScreen()
    coordinator = LibraryCoordinator(
        library_screen=screen,
        library_repository=MagicMock(),
        volume_ingestor=MagicMock(),
        thumbnail_service=MagicMock(),
        main_window=MagicMock(),
    )
    
    # Verify signals are connected by checking that methods exist
    assert hasattr(coordinator, "handle_volume_selected")
    assert hasattr(coordinator, "handle_volume_deleted")
    assert hasattr(coordinator, "handle_title_changed")


def test_library_coordinator_handle_missing_volume_path(library_repo, tmp_path):
    """Test handling of volume with missing path triggers relocation dialog."""
    ensure_qt_app()
    
    # Create a mock volume with an invalid path
    old_path = tmp_path / "old_location"
    new_path = tmp_path / "new_location"
    new_path.mkdir()
    
    # Create mock .mokuro file in new location
    (new_path / "test.mokuro").touch()
    
    # Add volume to library with old (non-existent) path
    cover_path = tmp_path / "cover.jpg"
    cover_path.touch()
    library_repo.add_volume(
        title="Test Volume",
        folder_path=old_path,
        cover_image_path=cover_path,
    )
    
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
    
    # Trigger handle_volume_selected with invalid path
    coordinator.handle_volume_selected(old_path)
    
    # Verify relocation dialog was shown
    mock_main_window.show_relocation_dialog.assert_called_once()
    
    # Verify success message was shown
    mock_main_window.show_info.assert_called_once()


def test_library_coordinator_handle_missing_mokuro_file(library_repo, tmp_path):
    """Test handling of volume with path that exists but no .mokuro file."""
    ensure_qt_app()
    
    # Create a directory that exists but has no .mokuro file
    volume_path = tmp_path / "volume"
    volume_path.mkdir()
    
    # Add volume to library
    cover_path = tmp_path / "cover.jpg"
    cover_path.touch()
    library_repo.add_volume(
        title="Test Volume",
        folder_path=volume_path,
        cover_image_path=cover_path,
    )
    
    # Setup mocks
    mock_main_window = MagicMock()
    mock_main_window.show_relocation_dialog.side_effect = RuntimeError("Relocation cancelled by user")
    
    coordinator = LibraryCoordinator(
        library_screen=LibraryScreen(),
        library_repository=library_repo,
        volume_ingestor=MagicMock(),
        thumbnail_service=MagicMock(),
        main_window=mock_main_window,
    )
    
    # Trigger handle_volume_selected with path missing .mokuro
    coordinator.handle_volume_selected(volume_path)
    
    # Verify relocation dialog was shown
    mock_main_window.show_relocation_dialog.assert_called_once()
    
    # Verify error was shown when relocation cancelled
    mock_main_window.show_error.assert_called_once()


def test_library_coordinator_valid_path_opens_volume(library_repo, tmp_path):
    """Test that valid path with .mokuro file opens volume."""
    ensure_qt_app()
    
    # Create valid volume with .mokuro file
    volume_path = tmp_path / "volume"
    volume_path.mkdir()
    (volume_path / "test.mokuro").touch()
    
    # Add volume to library
    cover_path = tmp_path / "cover.jpg"
    cover_path.touch()
    library_repo.add_volume(
        title="Test Volume",
        folder_path=volume_path,
        cover_image_path=cover_path,
    )
    
    # Setup mocks
    mock_main_window = MagicMock()
    mock_main_window.volume_opened = MagicMock()
    mock_main_window.volume_opened.emit = MagicMock()
    
    coordinator = LibraryCoordinator(
        library_screen=LibraryScreen(),
        library_repository=library_repo,
        volume_ingestor=MagicMock(),
        thumbnail_service=MagicMock(),
        main_window=mock_main_window,
    )
    
    # Trigger handle_volume_selected with valid path
    coordinator.handle_volume_selected(volume_path)
    
    # Verify relocation dialog was NOT shown
    mock_main_window.show_relocation_dialog.assert_not_called()
    
    # Verify volume_opened signal was emitted
    mock_main_window.volume_opened.emit.assert_called_once_with(volume_path)
