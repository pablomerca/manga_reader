"""MangaVolume entity - represents a complete manga volume."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from .manga_page import MangaPage


@dataclass
class MangaVolume:
    """Acts as the authoritative expert on a specific book's content."""
    
    title: str
    volume_path: Path
    pages: List[MangaPage] = field(default_factory=list)
    
    @property
    def total_pages(self) -> int:
        """Returns the total number of pages in this volume."""
        return len(self.pages)
    
    def get_page(self, page_number: int) -> MangaPage:
        """Retrieve a specific page by its number (0-indexed).

        Raises:
            ValueError: if page_number is out of bounds.
        """
        if 0 <= page_number < self.total_pages:
            return self.pages[page_number]
        raise ValueError(f"Page index {page_number} out of bounds for volume '{self.title}' with {self.total_pages} pages")
    
    def add_page(self, page: MangaPage) -> None:
        """Add a page to this volume."""
        self.pages.append(page)
    
    def validate_coordinates(self, page_number: int, x: float, y: float) -> bool:
        """Validate if coordinates are within a page's bounds."""
        if not (0 <= page_number < self.total_pages):
            return False
        page = self.get_page(page_number)
        return 0 <= x <= page.width and 0 <= y <= page.height
