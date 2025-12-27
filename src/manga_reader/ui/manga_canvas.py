"""Manga Canvas - Renders manga pages with OCR overlays using QWebEngineView."""

from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Signal

from manga_reader.core import MangaPage


# Template directory
TEMPLATES_DIR = Path(__file__).parent / "assets"


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
        # Load templates
        block_template = self._load_template("block_template.html")
        page_template = self._load_template("page_template.html")
        
        # Generate OCR block overlays
        blocks_html = ""
        for idx, block in enumerate(page.ocr_blocks):
            block_html = block_template.format(
                x=block.x,
                y=block.y,
                width=block.width,
                height=block.height,
                block_id=idx,
                text=block.full_text
            )
            blocks_html += block_html
        
        # Generate final HTML using safe substitution to avoid CSS braces conflict
        html = page_template.replace(
            "{image_filename}", page.image_path.name
        ).replace(
            "{blocks_html}", blocks_html
        )
        
        return html
    
    def _load_template(self, filename: str) -> str:
        """
        Load a template file from the assets directory.
        
        Args:
            filename: Name of the template file
            
        Returns:
            Template content as string
        """
        template_path = TEMPLATES_DIR / filename
        return template_path.read_text()
    
    def clear(self):
        """Clear the canvas."""
        self.current_page = None
        self.web_view.setHtml("<html><body></body></html>")
