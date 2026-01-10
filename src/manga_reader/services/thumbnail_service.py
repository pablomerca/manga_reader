"""Thumbnail generation service for library cover images.

Uses Qt QPixmap for image loading and scaling, caches thumbnails
under ~/.manga_reader/thumbnails/ using a stable path hash.

Fail-fast philosophy: methods raise RuntimeError on failure.
"""

import hashlib
import os
from pathlib import Path
from typing import Optional

from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


class ThumbnailService:
    """Generates and caches thumbnails for manga volumes.

    Target size: screen height * 0.25 (maintain aspect ratio).
    Output format: JPEG (.jpg)
    Cache dir: ~/.manga_reader/thumbnails/
    Filename: sha1 of folder_path string + .jpg
    """


    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        # TODO: make multi-platform compatible (Windows, macOS)
        base_dir = Path(cache_dir) if cache_dir else Path.home() / ".manga_reader" / "thumbnails"
        self.cache_dir = base_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Ensure a Qt application exists for QPixmap operations
        if QApplication.instance() is None:
            self._app = QApplication([])  # headless-safe; owned by service
        else:
            self._app = QApplication.instance()

    def generate_thumbnail(self, first_page_image: Path, volume_folder_path: Path) -> Path:
        """Generate and cache a thumbnail for the given volume.

        Args:
            first_page_image: Path to the first page image file.
            volume_folder_path: Absolute path to the volume's folder.

        Returns:
            Path to the cached thumbnail (.jpg).

        Raises:
            RuntimeError: If loading or saving the thumbnail fails.
        """
        img_path = Path(first_page_image)
        if not img_path.exists():
            raise RuntimeError(f"Image path does not exist: {img_path}")

        folder_path = Path(volume_folder_path).resolve()
        hash_name = hashlib.sha1(str(folder_path).encode("utf-8")).hexdigest()
        out_path = self.cache_dir / f"{hash_name}.jpg"

        # Load image
        pixmap = QPixmap(str(img_path))
        if pixmap.isNull():
            raise RuntimeError(f"Failed to load image: {img_path}")

        # Determine target height from primary screen
        screen = self._app.primaryScreen()
        if screen is None:
            # Fallback: assume 1080p if no screen (headless CI)
            screen_height = 1080
        else:
            screen_height = screen.size().height()
        target_height = int(screen_height * 0.25)

        # Scale while maintaining aspect ratio
        scaled = pixmap.scaledToHeight(target_height, mode=Qt.SmoothTransformation)
        if scaled.isNull():
            raise RuntimeError("Failed to scale image")

        # Save to cache
        if not scaled.save(str(out_path), "JPG"):
            raise RuntimeError(f"Failed to save thumbnail: {out_path}")

        return out_path
