#!/usr/bin/env python3
"""
Tests for LibraryRepository - validates library volume persistence.
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from manga_reader.io import DatabaseManager, LibraryRepository


@pytest.fixture
def db_connection():
    """Create an in-memory database for testing."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Initialize schema using the connection directly
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
    """Create a LibraryRepository with an in-memory database."""
    return LibraryRepository(db_connection)


def test_library_repository_add_volume(library_repo):
    """Test adding a volume to the library."""
    folder_path = Path("/test/manga/volume1")
    cover_path = Path("/cache/cover1.jpg")
    
    volume = library_repo.add_volume(
        title="Test Volume",
        folder_path=folder_path,
        cover_image_path=cover_path,
    )
    
    assert volume.id is not None
    assert volume.title == "Test Volume"
    assert volume.folder_path == folder_path.resolve()
    assert volume.cover_image_path == cover_path.resolve()
    assert volume.date_added > 0
    assert volume.last_opened > 0


def test_library_repository_get_volume_by_path(library_repo):
    """Test retrieving a volume by its folder path."""
    folder_path = Path("/test/manga/volume1")
    cover_path = Path("/cache/cover1.jpg")
    
    added_volume = library_repo.add_volume(
        title="Test Volume",
        folder_path=folder_path,
        cover_image_path=cover_path,
    )
    
    retrieved_volume = library_repo.get_volume_by_path(folder_path)
    
    assert retrieved_volume.id == added_volume.id
    assert retrieved_volume.title == "Test Volume"


def test_library_repository_get_volume_not_found(library_repo):
    """Test that getting a non-existent volume raises RuntimeError."""
    with pytest.raises(RuntimeError, match="Volume not found in library"):
        library_repo.get_volume_by_path(Path("/non/existent/path"))


def test_library_repository_get_all_volumes_empty(library_repo):
    """Test getting all volumes from empty library."""
    volumes = library_repo.get_all_volumes()
    
    assert volumes == []


def test_library_repository_get_all_volumes_multiple(library_repo):
    """Test retrieving multiple volumes in order of last_opened."""
    import time
    
    # Add volumes
    folder1 = Path("/test/manga/volume1")
    cover1 = Path("/cache/cover1.jpg")
    volume1 = library_repo.add_volume(
        title="Volume 1",
        folder_path=folder1,
        cover_image_path=cover1,
    )
    
    # Sleep to ensure different timestamp
    time.sleep(1)
    
    folder2 = Path("/test/manga/volume2")
    cover2 = Path("/cache/cover2.jpg")
    volume2 = library_repo.add_volume(
        title="Volume 2",
        folder_path=folder2,
        cover_image_path=cover2,
    )
    
    volumes = library_repo.get_all_volumes()
    
    assert len(volumes) == 2
    # Volume 2 should be first (added more recently)
    assert volumes[0].id == volume2.id
    assert volumes[1].id == volume1.id


def test_library_repository_add_duplicate_path_updates(library_repo):
    """Test that adding volume with same folder_path updates it."""
    folder_path = Path("/test/manga/volume1")
    cover1 = Path("/cache/cover1.jpg")
    cover2 = Path("/cache/cover2.jpg")
    
    volume1 = library_repo.add_volume(
        title="Original Title",
        folder_path=folder_path,
        cover_image_path=cover1,
    )
    original_id = volume1.id
    
    volume2 = library_repo.add_volume(
        title="Updated Title",
        folder_path=folder_path,
        cover_image_path=cover2,
    )
    
    # Should be the same volume (same ID)
    assert volume2.id == original_id
    assert volume2.title == "Updated Title"
    
    # Library should still have only 1 volume
    all_volumes = library_repo.get_all_volumes()
    assert len(all_volumes) == 1


def test_library_repository_update_title(library_repo):
    """Test updating a volume's title."""
    folder_path = Path("/test/manga/volume1")
    cover_path = Path("/cache/cover1.jpg")
    
    library_repo.add_volume(
        title="Original Title",
        folder_path=folder_path,
        cover_image_path=cover_path,
    )
    
    updated_volume = library_repo.update_title(
        folder_path=folder_path,
        new_title="New Title",
    )
    
    assert updated_volume.title == "New Title"
    
    # Verify it persists
    retrieved = library_repo.get_volume_by_path(folder_path)
    assert retrieved.title == "New Title"


def test_library_repository_update_title_empty_raises_error(library_repo):
    """Test that updating title to empty string raises RuntimeError."""
    folder_path = Path("/test/manga/volume1")
    cover_path = Path("/cache/cover1.jpg")
    
    library_repo.add_volume(
        title="Original Title",
        folder_path=folder_path,
        cover_image_path=cover_path,
    )
    
    with pytest.raises(RuntimeError, match="cannot be empty"):
        library_repo.update_title(folder_path=folder_path, new_title="")
    
    with pytest.raises(RuntimeError, match="cannot be empty"):
        library_repo.update_title(folder_path=folder_path, new_title="   ")


def test_library_repository_update_title_not_found(library_repo):
    """Test that updating title for non-existent volume raises RuntimeError."""
    with pytest.raises(RuntimeError, match="Volume not found"):
        library_repo.update_title(
            folder_path=Path("/non/existent/path"),
            new_title="New Title",
        )


def test_library_repository_update_last_opened(library_repo):
    """Test updating the last_opened timestamp."""
    folder_path = Path("/test/manga/volume1")
    cover_path = Path("/cache/cover1.jpg")
    
    volume = library_repo.add_volume(
        title="Test Volume",
        folder_path=folder_path,
        cover_image_path=cover_path,
    )
    original_timestamp = volume.last_opened
    
    # Wait a moment and update
    import time
    time.sleep(1)
    
    updated_volume = library_repo.update_last_opened(folder_path=folder_path)
    
    assert updated_volume.last_opened > original_timestamp


def test_library_repository_update_last_opened_not_found(library_repo):
    """Test that updating last_opened for non-existent volume raises RuntimeError."""
    with pytest.raises(RuntimeError, match="Volume not found"):
        library_repo.update_last_opened(
            folder_path=Path("/non/existent/path"),
        )


def test_library_repository_delete_volume(library_repo):
    """Test deleting a volume from the library."""
    folder_path = Path("/test/manga/volume1")
    cover_path = Path("/cache/cover1.jpg")
    
    library_repo.add_volume(
        title="Test Volume",
        folder_path=folder_path,
        cover_image_path=cover_path,
    )
    
    # Verify it exists
    assert len(library_repo.get_all_volumes()) == 1
    
    # Delete it
    library_repo.delete_volume(folder_path=folder_path)
    
    # Verify it's gone
    assert len(library_repo.get_all_volumes()) == 0
    
    # Verify querying it raises error
    with pytest.raises(RuntimeError, match="Volume not found in library"):
        library_repo.get_volume_by_path(folder_path)


def test_library_repository_delete_volume_not_found(library_repo):
    """Test that deleting non-existent volume raises RuntimeError."""
    with pytest.raises(RuntimeError, match="Volume not found"):
        library_repo.delete_volume(folder_path=Path("/non/existent/path"))


def test_library_repository_fails_fast_on_invalid_connection():
    """Test that LibraryRepository raises error on invalid connection."""
    with pytest.raises(RuntimeError, match="Database connection required"):
        LibraryRepository(None)
