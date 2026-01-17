"""Manga Canvas - Renders manga pages with OCR overlays using QWebEngineView."""

import json
from pathlib import Path
from typing import Optional, Set

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
    # Signal to notify Python that a word was clicked (noun, verb, adjective, etc.)
    wordClickedSignal = Signal(str, str, int, int, int, int)  # lemma, surface, x, y, page_index, block_id
    # Signal to notify Python that user wants to track a word
    trackWordSignal = Signal(str, str, str)  # lemma, reading, part_of_speech
    # Signal to notify Python that user wants to view context of a tracked word
    viewContextSignal = Signal(str)  # lemma

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

    @Slot(str, str, int, int, int, int)
    def requestWordLookup(self, lemma: str, surface: str, mouse_x: int, mouse_y: int, page_index: int, block_id: int):
        """Called from JS when a word span is clicked."""
        print(f"DEBUG: Python received word click: lemma='{lemma}', surface='{surface}', x={mouse_x}, y={mouse_y}, page_index={page_index}, block_id={block_id}")
        self.wordClickedSignal.emit(lemma, surface, mouse_x, mouse_y, page_index, block_id)

    @Slot(str, str, str)
    def trackWord(self, lemma: str, reading: str, part_of_speech: str):
        """Called from JS when user clicks Track Word button in popup."""
        print(f"DEBUG: Python received track word: lemma='{lemma}', reading='{reading}', pos='{part_of_speech}'")
        self.trackWordSignal.emit(lemma, reading, part_of_speech)

    @Slot(str)
    def viewWordContext(self, lemma: str):
        """Called from JS when user clicks View Context button in popup."""
        print(f"DEBUG: Python received view context: lemma='{lemma}'")
        self.viewContextSignal.emit(lemma)


class MangaCanvas(QWidget):
    """Renders manga JPEG with vertical Japanese text overlays using QWebEngineView."""
    
    # Signal emitted when user clicks on a text block
    block_clicked = Signal(int, int)  # x, y coordinates
    # Signal emitted for navigation (preventing browser scroll)
    navigation_requested = Signal(str) # "next" or "prev"
    # Signal emitted when user clicks on a word (noun, verb, adjective, etc.)
    word_clicked = Signal(str, str, int, int, int, int)  # lemma, surface, mouse_x, mouse_y, page_index, block_id
    # Signal emitted when user wants to track a word
    track_word_requested = Signal(str, str, str)  # lemma, reading, part_of_speech
    # Signal emitted when user wants to view all appearances of a tracked word
    view_word_context_requested = Signal(int)  # word_id
    # Signal emitted when user clicks View Context button in popup (by lemma)
    view_context_by_lemma_requested = Signal(str)  # lemma
    
    def __init__(self, morphology_service: MorphologyService):
        super().__init__()
        
        if morphology_service is None:
            raise ValueError("MorphologyService must not be None")

        # Initialize morphology service (dependency injection)
        self.morphology_service = morphology_service
        
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
        # Forward word click requests to canvas signal
        self.bridge.wordClickedSignal.connect(self.word_clicked)
        # Forward track word requests to canvas signal
        self.bridge.trackWordSignal.connect(self.track_word_requested)
        # Forward view context requests to canvas signal
        self.bridge.viewContextSignal.connect(self.view_context_by_lemma_requested)
        
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

    def render_pages(self, pages: list[MangaPage], tracked_lemmas: Set[str] = set()):
        """
        Render one or more manga pages with OCR overlays.
        
        Args:
            pages: List of MangaPage objects to render
            tracked_lemmas: Optional set of lemmas to highlight with black border
        """
        if not pages:
            self.clear()
            return

        # Reset any dictionary popup before redrawing
        self.hide_dictionary_popup()
        
        self.current_page = pages[0]  # Keep reference
        
        # Prepare data for JS
        data = self._prepare_data(pages, tracked_lemmas)
        
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
    
    def _prepare_data(self, pages: list[MangaPage], tracked_lemmas: Set[str]) -> dict:
        """
        Convert Python objects to JSON-serializable dict for JS.
        
        Args:
            pages: List of pages to serialize
            tracked_lemmas: Optional set of lemmas to mark as tracked
        """

        pages_data = []
        
        # Reverse pages for right-to-left reading order (Visual Order: Left -> Right)
        # If pages=[P1, P2], we want to display P2 on Left, P1 on Right.
        reversed_pages = list(reversed(pages))
        
        for page in reversed_pages:
            pages_data.append(self._serialize_page(page, tracked_lemmas))
            
        return {
            "pages": pages_data,
            "gap": 20,
            "trackedLemmas": list(tracked_lemmas)  # Include tracked lemmas for JS
        }

    def _serialize_page(self, page: MangaPage, tracked_lemmas: Set[str] = set()) -> dict:
        """
        Convert single page to dict with noun metadata.
        
        Each block includes a 'nouns' array with noun token information
        for JavaScript to use for highlighting and interaction.
        
        Args:
            page: The page to serialize
            tracked_lemmas: Optional set of tracked lemmas to mark words
        """
        blocks_data = []
        for idx, block in enumerate(page.ocr_blocks):
            font_size = self._calculate_font_size(block)
            
            # Extract words from block text for HTML wrapping
            words = self._extract_block_words(block.full_text)
            
            block_dict = {
                "id": idx,  # Simple ID for now
                "x": block.x,
                "y": block.y,
                "width": block.width,
                "height": block.height,
                "fontSize": font_size,
                "lines": block.text_lines,
                "words": [  # Metadata for JavaScript highlight wrapping (nouns + verbs)
                    {
                        "surface": token.surface,
                        "lemma": token.lemma,
                        "start": token.start_offset,
                        "end": token.end_offset,
                        "pos": token.pos,
                        "isTracked": token.lemma in tracked_lemmas,  # Mark tracked words
                    }
                    for token in words
                ],
            }
            blocks_data.append(block_dict)
            
        return {
            "imageUrl": QUrl.fromLocalFile(str(page.image_path)).toString(),
            "width": page.width,
            "height": page.height,
            "pageIndex": page.page_number,
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

    def _extract_block_words(self, text: str):
        """
        Extract words from OCR block text using morphology service.

        Args:
            text: Full text from OCR block

        Returns:
            List of Token objects representing words of interest (nouns + verbs)
        """
        if not text:
            return []

        # Collect POS filters once and extract in a single pass.
        noun_pos = ("NOUN", "NAME", "PLACE_NAME", "PRONOUN")
        verb_pos = ("VERB", "AUXILIARY_VERB")
        adjective_pos = ("ADJECTIVE", "ADJECTIVAL_NOUN")
        adverb_pos = ("ADVERB",)
        interested_pos = noun_pos + verb_pos + adjective_pos + adverb_pos

        return self.morphology_service.extract_words(text, interested_pos)

    def clear(self):
        """Clear the canvas."""
        self.current_page = None
        # Send empty data
        self.web_view.page().runJavaScript("updateView({pages: []});")
        self.hide_dictionary_popup()

    def show_dictionary_popup(self, payload: dict):
        """Forward dictionary popup payload to JS for rendering."""
        script = f"showWordPopup({json.dumps(payload)});"
        self.web_view.page().runJavaScript(script)

    def hide_dictionary_popup(self):
        """Hide the dictionary popup in JS."""
        self.web_view.page().runJavaScript("hideWordPopup();")

    def mark_popup_word_as_tracked(self):
        """Mark the currently displayed word as tracked in the popup.
        
        Dynamically updates the popup UI to hide the Track button and show
        the View Context button, indicating the word is now being tracked.
        """
        self.web_view.page().runJavaScript("window.markWordAsTracked();")

    def add_tracked_lemma(self, lemma: str):
        """
        Dynamically mark a lemma as tracked and update styling.
        
        Calls the JavaScript function `window.markLemmaAsTracked()` to update
        all instances of this lemma on the current page with tracked-word styling,
        without needing to re-render the entire page.
        
        Args:
            lemma: The lemma to mark as tracked
        """
        self.web_view.page().runJavaScript(f"window.markLemmaAsTracked('{lemma}');")

    def highlight_block_at_coordinates(self, crop_coords: dict):
        """
        Draw a red rectangle overlay on the canvas at specified coordinates.
        
        Calls JavaScript to highlight a block by drawing a red rectangle at the
        exact bounding box defined by crop_coordinates (x, y, width, height).
        This is used for visual navigation to word appearances in context panel.
        
        Args:
            crop_coords: Dictionary with keys 'x', 'y', 'width', 'height' (float values)
        """
        x = crop_coords.get('x', 0)
        y = crop_coords.get('y', 0)
        width = crop_coords.get('width', 100)
        height = crop_coords.get('height', 50)
        
        # Call JavaScript to draw the highlight rectangle
        script = f"window.highlightBlockAtCoordinates({x}, {y}, {width}, {height});"
        self.web_view.page().runJavaScript(script)
