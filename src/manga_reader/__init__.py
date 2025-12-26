"""
Manga Reader - A vocabulary companion for Japanese manga learners.

This package provides a desktop application for reading manga with:
- Mokuro OCR overlay support
- Dictionary lookups (future)
- Vocabulary tracking (future)
- Contextual recall (future)
"""

__version__ = "0.1.0"
__author__ = "Pablo-mercado"

# Make key components available at package level
from manga_reader.core import MangaVolume, MangaPage, OCRBlock
from manga_reader.io import VolumeIngestor

__all__ = [
    "MangaVolume",
    "MangaPage", 
    "OCRBlock",
    "VolumeIngestor",
]
