#!/usr/bin/env python3
"""
Tests for LibraryScreen - validates grid display and interactions.
"""

from pathlib import Path

from PySide6.QtWidgets import QApplication

from manga_reader.core import LibraryVolume
from manga_reader.ui import LibraryScreen


def ensure_qt_app():
    if QApplication.instance() is None:
        QApplication([])


def test_library_screen_empty_state():
    """Empty library should show empty state message."""
    ensure_qt_app()
    
    screen = LibraryScreen()
    screen.display_volumes([])
    
    # Empty label should not be hidden (show() was called)
    assert not screen.empty_label.isHidden()


def test_library_screen_displays_volumes():
    """Library screen should display volumes in grid."""
    ensure_qt_app()
    
    volumes = [
        LibraryVolume(
            id=1,
            title="Volume 1",
            folder_path=Path("/test/vol1"),
            cover_image_path=Path("/cache/cover1.jpg"),
            date_added=1000,
            last_opened=1000,
        ),
        LibraryVolume(
            id=2,
            title="Volume 2",
            folder_path=Path("/test/vol2"),
            cover_image_path=Path("/cache/cover2.jpg"),
            date_added=2000,
            last_opened=2000,
        ),
    ]
    
    screen = LibraryScreen()
    screen.display_volumes(volumes)
    
    # Empty label should be hidden
    assert screen.empty_label.isHidden()
    
    # Grid should have 2 tiles (plus the empty label widget)
    # Count excludes the empty_label
    tile_count = sum(
        1 for i in range(screen.grid_layout.count())
        if screen.grid_layout.itemAt(i).widget() != screen.empty_label
    )
    assert tile_count == 2


def test_library_screen_signals():
    """Verify that LibraryScreen has required signals."""
    ensure_qt_app()
    
    screen = LibraryScreen()
    
    # Check signals exist
    assert hasattr(screen, "volume_selected")
    assert hasattr(screen, "volume_deleted")
    assert hasattr(screen, "volume_title_changed")
