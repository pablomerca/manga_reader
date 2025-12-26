"""Manga Canvas - Renders manga pages with OCR overlays using QWebEngineView."""

from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Signal

from manga_reader.core import MangaPage


class MangaCanvas(QWidget):
    """Renders manga JPEG with vertical Japanese text overlays using QWebEngineView."""
    
    # Signal emitted when user clicks on a text block
    block_clicked = Signal(int, int)  # x, y coordinates
    
    def __init__(self):
        super().__init__()
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create web view for rendering
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)
        
        self.current_page: MangaPage | None = None
    
    def render_page(self, page: MangaPage):
        """
        Render a manga page with OCR overlays.
        
        Args:
            page: The MangaPage to render
        """
        self.current_page = page
        
        # Generate HTML content
        html = self._generate_html(page)
        
        # Load HTML into web view
        base_url = QUrl.fromLocalFile(str(page.image_path.parent) + "/")
        self.web_view.setHtml(html, base_url)
    
    def _generate_html(self, page: MangaPage) -> str:
        """
        Generate HTML with CSS for rendering the page with vertical text overlays.
        
        Args:
            page: The MangaPage to render
            
        Returns:
            HTML string
        """
        # Generate OCR block overlays
        blocks_html = ""
        for idx, block in enumerate(page.ocr_blocks):
            # Create div for each block with vertical text
            blocks_html += f"""
            <div class="ocr-block" style="
                position: absolute;
                left: {block.x}px;
                top: {block.y}px;
                width: {block.width}px;
                height: {block.height}px;
                writing-mode: vertical-rl;
                text-orientation: upright;
                font-size: 16px;
                color: transparent;
                cursor: pointer;
                user-select: none;
                z-index: 10;
            " data-block-id="{idx}">
                {block.full_text}
            </div>
            """
        
        # Complete HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    overflow: hidden;
                }}
                #page-container {{
                    position: relative;
                    display: inline-block;
                }}
                #page-image {{
                    display: block;
                    max-width: 100%;
                    height: auto;
                }}
                .ocr-block:hover {{
                    background-color: rgba(255, 255, 0, 0.3);
                }}
            </style>
        </head>
        <body>
            <div id="page-container">
                <img id="page-image" src="{page.image_path.name}" alt="Manga Page">
                {blocks_html}
            </div>
        </body>
        </html>
        """
        
        return html
    
    def clear(self):
        """Clear the canvas."""
        self.current_page = None
        self.web_view.setHtml("<html><body></body></html>")
