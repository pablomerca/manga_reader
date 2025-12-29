from unittest.mock import patch, MagicMock

from manga_reader.core.manga_page import MangaPage
from manga_reader.ui.manga_canvas import MangaCanvas


def test_generate_html_injects_dynamic_style_and_scales_uniformly():
    # Setup a canvas with mocked QWebEngineView size
    with patch('manga_reader.ui.manga_canvas.QWidget.__init__'), \
         patch('manga_reader.ui.manga_canvas.QVBoxLayout'), \
         patch('manga_reader.ui.manga_canvas.QWebEngineView') as MockView:
        mock_view_instance = MagicMock()
        mock_view_instance.width.return_value = 1000
        mock_view_instance.height.return_value = 1000
        MockView.return_value = mock_view_instance

        canvas = MangaCanvas()

        # Construct a page larger than viewport to force downscale
        page = MangaPage(
            page_number=0,
            image_path=MagicMock(name='image.jpg'),
            width=2000,
            height=1000,
            ocr_blocks=[]
        )
        # Patch image_path.name property
        page.image_path.name = 'image.jpg'

        html = canvas._generate_html(page)

        # Expected scale: min(1000/2000, 1000/1000) = 0.5
        assert 'transform: scale(0.5);' in html
        assert 'transform-origin: top left;' in html
        
        # Check centering logic:
        # scaled_width = 2000 * 0.5 = 1000. Viewport 1000. Offset = (1000-1000)/2 = 0
        assert 'left: 0px;' in html

        # Ensure natural dimensions are set for container and image
        assert '#page-container' in html
        assert '#page-image' in html
        assert 'width: 2000px;' in html
        assert 'height: 1000px;' in html

def test_centering_offset_calculation():
    # Setup a canvas with mocked QWebEngineView size
    with patch('manga_reader.ui.manga_canvas.QWidget.__init__'), \
         patch('manga_reader.ui.manga_canvas.QVBoxLayout'), \
         patch('manga_reader.ui.manga_canvas.QWebEngineView') as MockView:
        mock_view_instance = MagicMock()
        mock_view_instance.width.return_value = 1000
        mock_view_instance.height.return_value = 1000
        MockView.return_value = mock_view_instance

        canvas = MangaCanvas()

        # Page fits vertically, but is narrow: 500x1000
        # Scale: min(1000/500=2, 1000/1000=1) = 1.0
        page = MangaPage(
            page_number=0,
            image_path=MagicMock(name='image.jpg'),
            width=500,
            height=1000,
            ocr_blocks=[]
        )
        page.image_path.name = 'image.jpg'

        html = canvas._generate_html(page)

        assert 'transform: scale(1.0);' in html
        # Scaled width = 500 * 1 = 500
        # Offset = (1000 - 500) / 2 = 250
        assert 'left: 250.0px;' in html
