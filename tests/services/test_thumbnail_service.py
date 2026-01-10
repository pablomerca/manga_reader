#!/usr/bin/env python3
"""
Tests for ThumbnailService - validates thumbnail generation and caching.
"""

import hashlib
from pathlib import Path
import tempfile

from PySide6.QtGui import QPixmap, QColor
from PySide6.QtWidgets import QApplication

from manga_reader.services import ThumbnailService


def ensure_qt_app():
    if QApplication.instance() is None:
        QApplication([])


def test_thumbnail_service_generates_thumbnail():
    """Generate a thumbnail from a sample image and cache it."""
    ensure_qt_app()
    # Create a temporary cache dir
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir)
        svc = ThumbnailService(cache_dir=cache_dir)

        # Create a temporary image (200x300) and save it
        img_path = cache_dir / "sample.jpg"
        pix = QPixmap(200, 300)
        pix.fill(QColor("red"))
        assert pix.save(str(img_path), "JPG")

        # Define a volume folder path
        vol_path = Path("/test/manga/volume1").resolve()

        # Generate thumbnail
        out_path = svc.generate_thumbnail(first_page_image=img_path, volume_folder_path=vol_path)

        # Validate output path and file
        assert out_path.exists()
        assert out_path.parent == cache_dir

        # Validate naming: sha1 of folder path + .jpg
        expected_name = hashlib.sha1(str(vol_path).encode("utf-8")).hexdigest() + ".jpg"
        assert out_path.name == expected_name

        # Validate size: scaled to target height maintaining aspect ratio
        out_pix = QPixmap(str(out_path))
        assert not out_pix.isNull()
        screen = QApplication.instance().primaryScreen()
        screen_height = 1080 if screen is None else screen.size().height()
        target_height = int(screen_height * 0.25)
        assert out_pix.height() == target_height
        # Aspect ratio maintained
        assert out_pix.width() > 0


def test_thumbnail_service_invalid_image_path_raises():
    """Invalid image path should raise RuntimeError (fail-fast)."""
    ensure_qt_app()
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir)
        svc = ThumbnailService(cache_dir=cache_dir)
        bad_img = cache_dir / "missing.jpg"
        vol_path = Path("/test/manga/volume1")
        try:
            svc.generate_thumbnail(first_page_image=bad_img, volume_folder_path=vol_path)
            assert False, "Expected RuntimeError for missing image path"
        except RuntimeError as e:
            assert "does not exist" in str(e)
