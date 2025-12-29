"""Manga Canvas - Renders manga pages with OCR overlays using QWebEngineView."""

from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget

from manga_reader.core import MangaPage, OCRBlock

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
        Generate HTML with CSS for rendering the page(s).
        Acts as a coordinator for layout and content generation.
        """
        # 1. Load Templates
        page_template = self._load_template("page_template.html")

        # 2. Generate Content HTML (for the single page)
        # Future extensibility: iterate over a list of pages here
        content_html, total_width, max_height = self._generate_page_html(page)

        # 3. Calculate Layout & Scale
        try:
            viewport_w = max(int(self.web_view.width()), 1)
            viewport_h = max(int(self.web_view.height()), 1)
        except Exception:
            viewport_w, viewport_h = total_width, max_height

        scale = min(viewport_w / max(total_width, 1), viewport_h / max(max_height, 1))
        if scale <= 0:
            scale = 1.0

        # 4. Inject Dynamic CSS (Layout)
        # We apply the scale to the content wrapper.
        # Flexbox in the template handles the centering.
        dynamic_style: str = (
            "\n<style id=\"dynamic-fit-style\">\n"
            f"#content-wrapper {{ \n"
            f"  width: {total_width}px;\n"
            f"  height: {max_height}px;\n"
            f"  transform: scale({scale});\n"
            f"  transform-origin: center center;\n"
            "}\n"
            "</style>\n"
        )

        # 5. Assemble Final HTML
        html = page_template.replace("{content_html}", content_html)
        
        if "</head>" in html:
            html = html.replace("</head>", dynamic_style + "</head>")
        else:
            html = dynamic_style + html
        
        return html

    def _generate_page_html(self, page: MangaPage) -> tuple[str, int, int]:
        """
        Generates HTML for a single page container including image and OCR blocks.
        
        Returns:
            Tuple of (html_string, width, height)
        """
        blocks_html = self._generate_ocr_html(page)
        
        # Structure for a single page
        # Note: we use inline styles for the page container to set its exact size
        # This allows multiple pages to be positioned relatively if needed in future
        page_html = (
            f'<div class="page-container" style="width: {page.width}px; height: {page.height}px;">\n'
            f'    <img class="page-image" src="{page.image_path.name}" alt="Manga Page">\n'
            f'    {blocks_html}\n'
            f'</div>'
        )
        return page_html, page.width, page.height

    def _generate_ocr_html(self, page: MangaPage) -> str:
        """Generates HTML for all OCR blocks on the page."""
        block_template = self._load_template("block_template.html")
        line_template = self._load_template("line_template.html")
        
        blocks_html = ""
        for idx, block in enumerate(page.ocr_blocks):
            font_size = self._calculate_font_size(block)

            lines_html = ""
            for line_text in block.text_lines:
                lines_html += line_template.format(line_text=line_text)
            
            blocks_html += block_template.format(
                x=block.x,
                y=block.y,
                width=block.width,
                height=block.height,
                font_size=font_size,
                block_id=idx,
                lines_html=lines_html
            )
        return blocks_html
    
    def _calculate_font_size(self, block: OCRBlock) -> int:
        """
        Calculates the largest integer font size such that the text fills the block.
        """
        if not block.text_lines:
            return 12  # Default fallback
            
        # Constants
        SAFETY_MARGIN = 0.90  # 90% to be safe against rendering quirks
        MIN_FONT_SIZE = 10
        MAX_FONT_SIZE = 200
        
        # 1. Height Constraint: Longest line must fit vertically
        max_chars = max((len(line) for line in block.text_lines), default=0)
        if max_chars == 0:
            return 12
            
        # height = char_size * num_chars
        size_by_height = (block.height * SAFETY_MARGIN) / max_chars
        
        # 2. Width Constraint: All lines must fit horizontally
        # width = font_size * num_lines
        num_lines = len(block.text_lines)
        size_by_width = (block.width * SAFETY_MARGIN) / num_lines
        
        # Optimal size is the minimum of constraints
        optimal_size = min(size_by_height, size_by_width)
        
        return max(MIN_FONT_SIZE, min(int(optimal_size), MAX_FONT_SIZE))

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
