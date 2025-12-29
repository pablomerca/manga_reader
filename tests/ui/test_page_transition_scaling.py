from unittest.mock import patch, MagicMock
from pathlib import Path

from manga_reader.core.manga_page import MangaPage
from manga_reader.ui.manga_canvas import MangaCanvas


def test_per_page_scale_recalculation_on_transition():
    # Mock QWebEngineView with fixed viewport size 1200x800
    with patch('manga_reader.ui.manga_canvas.QWidget.__init__'), \
         patch('manga_reader.ui.manga_canvas.QVBoxLayout'), \
         patch('manga_reader.ui.manga_canvas.QWebEngineView') as MockView:
        mock_view_instance = MagicMock()
        mock_view_instance.width.return_value = 1200
        mock_view_instance.height.return_value = 800
        MockView.return_value = mock_view_instance

        canvas = MangaCanvas()

        # Landscape page (wide): 2400x1200 => scale min(1200/2400=0.5, 800/1200≈0.666)=0.5
        landscape_page = MangaPage(
            page_number=0,
            image_path=Path('/tmp/landscape.jpg'),
            width=2400,
            height=1200,
            ocr_blocks=[]
        )

        # Portrait page (tall): 1200x2400 => scale min(1200/1200=1.0, 800/2400≈0.333)=≈0.3333
        portrait_page = MangaPage(
            page_number=1,
            image_path=Path('/tmp/portrait.jpg'),
            width=1200,
            height=2400,
            ocr_blocks=[]
        )

        # Render landscape then portrait
        canvas.render_page(landscape_page)
        canvas.render_page(portrait_page)

        # Capture HTML passed to setHtml for the two renders
        calls = mock_view_instance.setHtml.call_args_list
        assert len(calls) >= 2
        first_html = calls[0].args[0]
        second_html = calls[1].args[0]

        # First render scales to 0.5 and sets container dims to 2400x1200
        assert '--content-scale: 0.5;' in first_html
        assert '--content-width: 2400px;' in first_html
        assert '--content-height: 1200px;' in first_html

        # Second render re-computes scale (~0.3333) and sets container dims to 1200x2400
        assert '--content-scale: 0.333' in second_html  # robust prefix check
        assert '--content-width: 1200px;' in second_html
        assert '--content-height: 2400px;' in second_html
