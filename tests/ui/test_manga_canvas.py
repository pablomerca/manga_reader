from unittest.mock import patch

import pytest

from manga_reader.core.ocr_block import OCRBlock
from manga_reader.ui.manga_canvas import MangaCanvas


@pytest.fixture
def manga_canvas():
    """Fixture to create MangaCanvas instance with mocked init."""
    with patch('manga_reader.ui.manga_canvas.QWidget.__init__'), \
         patch('manga_reader.ui.manga_canvas.QVBoxLayout'), \
         patch('manga_reader.ui.manga_canvas.QWebEngineView'):
        canvas = MangaCanvas()
        return canvas

def test_calculate_font_size_height_constraint(manga_canvas):
    """Test font size calculation when limited by height."""
    # Height 400, 10 chars -> max 40px/char (approx)
    # Width 100, 1 line -> max 100px/char
    block = OCRBlock(x=0, y=0, width=100, height=400, text_lines=["あ" * 10])
    
    size = manga_canvas._calculate_font_size(block)
    
    # Expected: (400 * 0.90) / 10 = 36
    assert size == 36

def test_calculate_font_size_width_constraint(manga_canvas):
    """Test font size calculation when limited by width."""
    # Height 400, 2 chars -> max 200px/char
    # Width 100, 5 lines -> max 20px/char (approx)
    block = OCRBlock(x=0, y=0, width=100, height=400, text_lines=["あ"] * 5)
    
    size = manga_canvas._calculate_font_size(block)
    
    # Expected: (100 * 0.90) / 5 = 18
    assert size == 18

def test_calculate_font_size_min_limit(manga_canvas):
    """Test that font size does not go below minimum."""
    # Very small box
    block = OCRBlock(x=0, y=0, width=10, height=10, text_lines=["あ" * 10])
    
    size = manga_canvas._calculate_font_size(block)
    
    assert size == 10  # MIN_FONT_SIZE

def test_calculate_font_size_max_limit(manga_canvas):
    """Test that font size does not exceed maximum."""
    # Very large box
    block = OCRBlock(x=0, y=0, width=1000, height=1000, text_lines=["あ"])
    
    size = manga_canvas._calculate_font_size(block)
    
    assert size == 200  # MAX_FONT_SIZE
