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
    
    def render_pages(self, pages: list[MangaPage]):
        """
        Render one or more manga pages with OCR overlays.
        
        Args:
            pages: List of MangaPage objects to render
        """
        if not pages:
            self.clear()
            return
        
        self.current_page = pages[0]  # Keep reference to first page
        
        # Generate HTML content
        html = self._generate_html(pages)
        
        # Load HTML into web view - use first page's directory as base
        base_url = QUrl.fromLocalFile(str(pages[0].image_path.parent) + "/")
        self.web_view.setHtml(html, base_url)
    
    def render_page(self, page: MangaPage):
        """
        Render a single manga page with OCR overlays (legacy method).
        
        Args:
            page: The MangaPage to render
        """
        self.render_pages([page])
    
    def _generate_html(self, pages: list[MangaPage]) -> str:
        """
        Generate HTML with CSS for rendering the page(s).
        Acts as a coordinator for layout and content generation.
        
        Args:
            pages: List of MangaPage objects to render (1 or 2 pages)
        """
        # 1. Load Templates
        page_template = self._load_template("page_template.html")

        # 2. Generate Content HTML for all pages
        content_html, total_width, max_height = self._generate_pages_html(pages)

        # 3. Calculate Layout & Scale
        try:
            viewport_w = max(int(self.web_view.width()), 1)
            viewport_h = max(int(self.web_view.height()), 1)
        except Exception:
            viewport_w, viewport_h = total_width, max_height

        scale = min(viewport_w / max(total_width, 1), viewport_h / max(max_height, 1))
        if scale <= 0:
            scale = 1.0

        # 4. Prepare CSS Variables
        # We apply the scale to the content wrapper via CSS variables
        page_gap = 20  # Gap between pages in double page mode
        
        css_vars = (
            f"--content-width: {total_width}px; "
            f"--content-height: {max_height}px; "
            f"--content-scale: {scale}; "
            f"--page-gap: {page_gap}px;"
        )

        # 5. Assemble Final HTML
        html = page_template.replace("{css_vars}", css_vars).replace("{content_html}", content_html)
        
        return html
    
    def _generate_pages_html(self, pages: list[MangaPage]) -> tuple[str, int, int]:
        """
        Generates HTML for one or more page containers.
        
        For manga (right-to-left reading), pages are displayed in reverse order:
        - In double page mode: current page on right, next page on left
        
        Args:
            pages: List of MangaPage objects to render
            
        Returns:
            Tuple of (html_string, total_width, max_height)
        """
        if not pages:
            return "", 0, 0
        
        page_gap = 20  # Gap between pages
        pages_html_list = []
        total_width = 0
        max_height = 0
        
        # Reverse pages for right-to-left reading order
        # (current page appears on the right, next page on the left)
        reversed_pages = list(reversed(pages))
        
        for page in reversed_pages:
            page_html, page_width, page_height = self._generate_page_html(page)
            pages_html_list.append(page_html)
            total_width += page_width
            max_height = max(max_height, page_height)
        
        # Add gap spacing for multiple pages
        if len(pages) > 1:
            total_width += page_gap * (len(pages) - 1)
        
        combined_html = "\n".join(pages_html_list)
        return combined_html, total_width, max_height

    def _generate_page_html(self, page: MangaPage) -> tuple[str, int, int]:
        """
        Generates HTML for a single page container including image and OCR blocks.
        
        Returns:
            Tuple of (html_string, width, height)
        """
        blocks_html = self._generate_ocr_html(page)
        
        container_template = self._load_template("page_container_template.html")
        
        page_html = container_template.format(
            width=page.width,
            height=page.height,
            image_name=page.image_path.name,
            blocks_html=blocks_html
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
