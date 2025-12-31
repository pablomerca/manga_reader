"""MangaPage entity - represents a single page with OCR blocks."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .ocr_block import OCRBlock


@dataclass
class MangaPage:
    """Represents a single page containing page dimensions and a list of OCR blocks."""
    
    page_number: int
    image_path: Path
    width: int
    height: int
    ocr_blocks: List[OCRBlock] = field(default_factory=list)
    
    def find_block_at_position(self, x: float, y: float) -> Optional[OCRBlock]:
        """Find the OCR block that contains the given coordinates."""
        for block in self.ocr_blocks:
            if block.contains_point(x, y):
                return block
        return None
    
    def get_all_text(self) -> str:
        """Returns all text content on this page."""
        return "\n".join(block.full_text for block in self.ocr_blocks)
    
    def is_portrait(self) -> bool:
        """Returns True if the page is in portrait orientation (height > width)."""
        return self.height > self.width
