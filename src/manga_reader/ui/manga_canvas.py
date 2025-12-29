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
        Generate HTML with CSS for rendering the page with vertical text overlays.
        Uses lazy rendering with text hidden by default and visible on hover.
        
        Args:
            page: The MangaPage to render
            
        Returns:
            HTML string
        """
        # Load templates
        block_template = self._load_template("block_template.html")
        line_template = self._load_template("line_template.html")
        page_template = self._load_template("page_template.html")
        
        # Generate OCR block overlays
        blocks_html = ""
        for idx, block in enumerate(page.ocr_blocks):
            # Calculate optimal font size for this block
            font_size = self._calculate_font_size(block)

            # Generate HTML for each text line within the block
            lines_html = ""
            for line_text in block.text_lines:
                line_html = line_template.format(line_text=line_text)
                lines_html += line_html
            
            # Generate block HTML with lines
            block_html = block_template.format(
                x=block.x,
                y=block.y,
                width=block.width,
                height=block.height,
                font_size=font_size,
                block_id=idx,
                lines_html=lines_html
            )
            blocks_html += block_html
        
        # Generate final HTML using safe substitution to avoid CSS braces conflict
        html = page_template.replace(
            "{image_filename}", page.image_path.name
        ).replace(
            "{blocks_html}", blocks_html
        )

        # Compute scale to fit the entire page within the current viewport
        try:
            viewport_w = max(int(self.web_view.width()), 1)
            viewport_h = max(int(self.web_view.height()), 1)
        except Exception:
            viewport_w, viewport_h = page.width, page.height

        # Fit-to-screen scale: ensure both dimensions fit
        scale = min(viewport_w / max(page.width, 1), viewport_h / max(page.height, 1))
        if scale <= 0:
            scale = 1.0
            
        # Calculate horizontal centering offset
        scaled_width: float = page.width * scale
        x_offset: float = max(0, (viewport_w - scaled_width) / 2)

        # Inject dynamic CSS to scale both image and overlays uniformly
        dynamic_style = (
            "\n<style id=\"dynamic-fit-style\">\n"
            f"#page-container {{\n"
            f"  width: {page.width}px;\n"
            f"  height: {page.height}px;\n"
            f"  transform: scale({scale});\n"
            f"  transform-origin: top left;\n"
            f"  position: absolute;\n"
            f"  left: {x_offset}px;\n"
            f"  top: 0px;\n"
            "}\n"
            f"#page-image {{\n"
            f"  width: {page.width}px;\n"
            f"  height: {page.height}px;\n"
            "}\n"
            "</style>\n"
        )

        # Place the dynamic style inside the <head> to override defaults
        if "</head>" in html:
            html = html.replace("</head>", dynamic_style + "</head>")
        else:
            # Fallback: prepend style if template was modified
            html = dynamic_style + html
        
        return html
    
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
