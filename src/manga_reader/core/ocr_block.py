"""OCR Block entity - represents a single text area with bounding box."""

from dataclasses import dataclass
from typing import List


@dataclass
class OCRBlock:
    """Represents a single text area with its bounding box coordinates, orientation, and raw lines of text."""
    
    x: float
    y: float
    width: float
    height: float
    text_lines: List[str]
    orientation: str = "vertical"  # Default for Japanese manga
    
    @property
    def full_text(self) -> str:
        """Returns all text lines concatenated."""
        return "".join(self.text_lines)
    
    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is within this block's bounding box."""
        return (self.x <= x <= self.x + self.width and 
                self.y <= y <= self.y + self.height)
