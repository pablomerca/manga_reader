"""Manga Canvas - Renders manga pages with OCR overlays using QWebEngineView."""

import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QEvent, QObject, Qt, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget

from manga_reader.core import MangaPage, OCRBlock
from manga_reader.services import MorphologyService

# Template directory
TEMPLATES_DIR = Path(__file__).parent / "assets"


class WebConnector(QObject):
    """Bridge between Python and JavaScript."""
    
    # We no longer need a signal here to push data. 
    # We will use runJavaScript() for that.
    
    # Signal to notify Python that a block was clicked
    blockClickedSignal = Signal(int, int)  # id, ? might pass ID or metadata
    navigationSignal = Signal(str)  # "next" | "prev"
    # Signal to notify Python that a noun was clicked
    nounClickedSignal = Signal(str, str, int, int)  # lemma, surface, x, y

    def __init__(self):
        super().__init__()

    @Slot(int)
    def blockClicked(self, block_id):
        """Called from JS when a block is clicked."""
        print(f"DEBUG: Python received block click: {block_id}")
        # For now we just print or emit a generic signal.
        # Ideally we map ID back to page/block. 
        # But for this refactor let's just keep the connection alive.
        pass

    @Slot(str)
    def requestNavigation(self, direction: str):
        """Called from JS to request navigation (left/right arrows)."""
        self.navigationSignal.emit(direction)

    @Slot(str, str, int, int)
    def requestNounLookup(self, lemma: str, surface: str, mouse_x: int, mouse_y: int):
        """Called from JS when a noun span is clicked."""
        print(f"DEBUG: Python received noun click: lemma='{lemma}', surface='{surface}', x={mouse_x}, y={mouse_y}")
        self.nounClickedSignal.emit(lemma, surface, mouse_x, mouse_y)


class MangaCanvas(QWidget):
    """Renders manga JPEG with vertical Japanese text overlays using QWebEngineView."""
    
    # Signal emitted when user clicks on a text block
    block_clicked = Signal(int, int)  # x, y coordinates
    # Signal emitted for navigation (preventing browser scroll)
    navigation_requested = Signal(str) # "next" or "prev"
    # Signal emitted when user clicks on a noun
    noun_clicked = Signal(str, str, int, int)  # lemma, surface, mouse_x, mouse_y
    
    def __init__(self, morphology_service: Optional[MorphologyService] = None):
        super().__init__()
        
        # Initialize morphology service (dependency injection; can be None if not available)
        self.morphology_service = morphology_service or MorphologyService()
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create web view for rendering
        self.web_view = QWebEngineView()
        
        # Install event filter to capture keys before browser
        self.web_view.installEventFilter(self)
        # Often the focus proxy handles the actual input events in WebEngine
        if self.web_view.focusProxy():
            self.web_view.focusProxy().installEventFilter(self)
        
        # 1. Setup WebChannel
        print("DEBUG: Setting up QWebChannel...")
        self.bridge = WebConnector()
        self.channel = QWebChannel()
        self.channel.registerObject("connector", self.bridge)
        self.web_view.page().setWebChannel(self.channel)
        print("DEBUG: QWebChannel setup complete. Connector registered.")

        # Forward JS navigation requests to canvas signal
        self.bridge.navigationSignal.connect(self.navigation_requested)
        # Forward noun click requests to canvas signal
        self.bridge.nounClickedSignal.connect(self.noun_clicked)
        
        layout.addWidget(self.web_view)
        
        self.current_page: MangaPage | None = None
        
        # 2. Load the static HTML viewer
        viewer_path = TEMPLATES_DIR / "viewer.html"
        print(f"DEBUG: Loading viewer from {viewer_path}")
        self.web_view.load(QUrl.fromLocalFile(str(viewer_path)))

    def eventFilter(self, obj, event):
        """Intercept key events to prevent browser scrolling/navigation."""
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Left:
                self.navigation_requested.emit("next") # RTL: Left is Next
                return True # Consume event
            elif key == Qt.Key.Key_Right:
                self.navigation_requested.emit("prev") # RTL: Right is Previous
                return True # Consume event
        
        return super().eventFilter(obj, event)

    def render_pages(self, pages: list[MangaPage]):
        """
        Render one or more manga pages with OCR overlays.
        
        Args:
            pages: List of MangaPage objects to render
        """
        if not pages:
            self.clear()
            return
        
        self.current_page = pages[0]  # Keep reference
        
        # Prepare data for JS
        data = self._prepare_data(pages)
        
        # Send data to JS via runJavaScript (Most robust method)
        # We assume 'updateView' is available globally in the loaded page.
        # json.dumps converts the dict to a JSON string that JS can parse or eval.
        json_data = json.dumps(data)
        script = f"updateView({json_data});"
        
        self.web_view.page().runJavaScript(script)
    
    def render_page(self, page: MangaPage):
        """
        Render a single manga page with OCR overlays (legacy method).
        
        Args:
            page: The MangaPage to render
        """
        self.render_pages([page])
    
    def _prepare_data(self, pages: list[MangaPage]) -> dict:
        """
        Convert Python objects to JSON-serializable dict for JS.
        """
        pages_data = []
        
        # Reverse pages for right-to-left reading order (Visual Order: Left -> Right)
        # If pages=[P1, P2], we want to display P2 on Left, P1 on Right.
        reversed_pages = list(reversed(pages))
        
        for page in reversed_pages:
            pages_data.append(self._serialize_page(page))
            
        return {
            "pages": pages_data,
            "gap": 20
        }

    def _serialize_page(self, page: MangaPage) -> dict:
        """
        Convert single page to dict with noun metadata.
        
        Each block includes a 'nouns' array with noun token information
        for JavaScript to use for highlighting and interaction.
        """
        blocks_data = []
        for idx, block in enumerate(page.ocr_blocks):
            font_size = self._calculate_font_size(block)
            
            # Extract nouns from block text for HTML wrapping
            nouns = self._extract_block_nouns(block.full_text)
            
            block_dict = {
                "id": idx,  # Simple ID for now
                "x": block.x,
                "y": block.y,
                "width": block.width,
                "height": block.height,
                "fontSize": font_size,
                "lines": block.text_lines,
                "nouns": [  # NEW: noun metadata for JavaScript highlight wrapping
                    {
                        "surface": token.surface,
                        "lemma": token.lemma,
                        "start": token.start_offset,
                        "end": token.end_offset,
                    }
                    for token in nouns
                ],
            }
            blocks_data.append(block_dict)
            
        return {
            "imageUrl": QUrl.fromLocalFile(str(page.image_path)).toString(),
            "width": page.width,
            "height": page.height,
            "blocks": blocks_data
        }
    
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

    def _extract_block_nouns(self, text: str):
        """
        Extract nouns from OCR block text using morphology service.
        
        Args:
            text: Full text from OCR block
            
        Returns:
            List of Token objects representing nouns
        """
        if not text or not self.morphology_service:
            return []
        
        return self.morphology_service.extract_nouns(text)

    def clear(self):
        """Clear the canvas."""
        self.current_page = None
        # Send empty data
        self.web_view.page().runJavaScript("updateView({pages: []});")

