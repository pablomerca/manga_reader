from pathlib import Path
from unittest.mock import patch, MagicMock

from PySide6.QtCore import QUrl

from manga_reader.core.manga_page import MangaPage
from manga_reader.core.ocr_block import OCRBlock
from manga_reader.ui.manga_canvas import MangaCanvas


def test_prepare_data_structure():
    """Test that _prepare_data produces the correct JSON structure for the frontend."""
    with patch('manga_reader.ui.manga_canvas.QWidget.__init__'), \
         patch('manga_reader.ui.manga_canvas.QVBoxLayout'), \
         patch('manga_reader.ui.manga_canvas.QWebEngineView'), \
         patch('manga_reader.ui.manga_canvas.QWebChannel'), \
         patch('manga_reader.ui.manga_canvas.WebConnector'):
        
        canvas = MangaCanvas(morphology_service=MagicMock())
        
        # Create a sample page with one OCR block
        block = OCRBlock(x=10, y=20, width=100, height=200, text_lines=["Hello"])
        page = MangaPage(
            page_number=1,
            image_path=Path('/tmp/test_image.jpg'),
            width=800,
            height=1200,
            ocr_blocks=[block]
        )
        
        data = canvas._prepare_data([page])
        
        assert "pages" in data
        assert "gap" in data
        assert len(data["pages"]) == 1
        
        page_data = data["pages"][0]
        # Check standard fields
        assert page_data["width"] == 800
        assert page_data["height"] == 1200
        expected_url = QUrl.fromLocalFile('/tmp/test_image.jpg').toString()
        assert page_data["imageUrl"] == expected_url
        
        # Check blocks
        assert len(page_data["blocks"]) == 1
        block_data = page_data["blocks"][0]
        assert block_data["x"] == 10
        assert block_data["y"] == 20
        assert block_data["width"] == 100
        assert block_data["height"] == 200
        assert block_data["lines"] == ["Hello"]
        assert "fontSize" in block_data

def test_prepare_data_ordering_rtl():
    """Test that pages are reversed for RTL reading (visual Left-to-Right)."""
    with patch('manga_reader.ui.manga_canvas.QWidget.__init__'), \
         patch('manga_reader.ui.manga_canvas.QVBoxLayout'), \
         patch('manga_reader.ui.manga_canvas.QWebEngineView'), \
         patch('manga_reader.ui.manga_canvas.QWebChannel'), \
         patch('manga_reader.ui.manga_canvas.WebConnector'):
        
        canvas = MangaCanvas(morphology_service=MagicMock())
        
        page1 = MangaPage(0, Path('p1.jpg'), 100, 100, [])
        page2 = MangaPage(1, Path('p2.jpg'), 100, 100, [])
        
        # Input order: [Page 1 (Right), Page 2 (Left)]
        # Expected visual order: [Page 2, Page 1]
        data = canvas._prepare_data([page1, page2])
        
        assert len(data["pages"]) == 2
        # Check that the first element in the list (Visual Left) is Page 2
        assert "p2.jpg" in data["pages"][0]["imageUrl"]
        # Check that the second element in the list (Visual Right) is Page 1
        assert "p1.jpg" in data["pages"][1]["imageUrl"]
