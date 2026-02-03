"""Dictionary Side Panel - Displays full word/kanji entries with clickable kanji."""

from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from manga_reader.services import (
    BreadcrumbItem,
    DictionaryEntryFull,
    DictionaryLookupResult,
    KanjiEntry,
)


class ClickableKanjiLabel(QLabel):
    """
    Custom QLabel that emits signal when individual kanji characters are clicked.
    Calculates which kanji was clicked based on cursor position.
    Supports displaying furigana (kana reading) above the text.
    """
    
    kanji_clicked = Signal(str)  # Emits the clicked kanji character
    
    def __init__(self, text: str = "", is_header: bool = False, reading: str = ""):
        super().__init__()
        self.text_content = text
        self.is_header = is_header
        self.reading = reading
        self._render_clickable_kanji(text, reading)
    
    def _is_kanji(self, char: str) -> bool:
        """Check if character is kanji."""
        if not char:
            return False
        code = ord(char)
        return (
            (0x4E00 <= code <= 0x9FFF) or  # CJK Unified Ideographs
            (0x3400 <= code <= 0x4DBF) or  # CJK Extension A
            (0x20000 <= code <= 0x2A6DF) or  # CJK Extension B
            (0x2A700 <= code <= 0x2B73F) or  # CJK Extension C
            (0x2B740 <= code <= 0x2B81F) or  # CJK Extension D
            (0x2B820 <= code <= 0x2CEAF) or  # CJK Extension E
            (0xF900 <= code <= 0xFAFF) or  # CJK Compatibility Ideographs
            (0x2F800 <= code <= 0x2FA1F)  # CJK Compatibility Ideographs Supplement
        )
    
    def _render_clickable_kanji(self, text: str, reading: str = ""):
        """Render text with clickable kanji styled appropriately, optionally with furigana."""
        html_parts = []
        
        # If reading is provided and this is a header, create a container with furigana above
        if reading and self.is_header:
            # Use a div with furigana positioned above using a table-like structure
            html_parts.append('<div style="display: inline-block; text-align: center;">')
            html_parts.append(f'<div style="font-size: 14px; color: #b0b0b0; line-height: 1.2;">{reading}</div>')
            html_parts.append('<div style="line-height: 1.2;">')
        
        for char in text:
            if self._is_kanji(char):
                if self.is_header:
                    # Header style: larger (28px), bold, lighter blue for easy clicking
                    html_parts.append(
                        f'<span style="color: #66b3ff; cursor: pointer; text-decoration: underline; '
                        f'font-size: 28px; font-weight: bold;">{char}</span>'
                    )
                else:
                    # Regular style: standard clickable kanji
                    html_parts.append(
                        f'<span style="color: #0066cc; cursor: pointer; text-decoration: underline;">{char}</span>'
                    )
            else:
                # Non-kanji characters
                if self.is_header:
                    html_parts.append(f'<span style="font-size: 24px; font-weight: bold;">{char}</span>')
                else:
                    html_parts.append(char)
        
        # Close the furigana container if it was opened
        if reading and self.is_header:
            html_parts.append('</div></div>')
        
        self.setText(''.join(html_parts))
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
    
    def mousePressEvent(self, event):
        """Handle mouse click - determine which character was clicked."""
        from PySide6.QtGui import QFont
        
        cursor_pos = event.pos()
        x_pos = cursor_pos.x()
        accumulated_width = 0
        
        for char_idx, char in enumerate(self.text_content):
            # Create font with the actual styled size for accurate width calculation
            styled_font = QFont(self.font())
            
            if self._is_kanji(char):
                # Kanji use larger font in headers (28px in HTML)
                if self.is_header:
                    styled_font.setPixelSize(28)
                    styled_font.setBold(True)
                else:
                    # Regular kanji use default size
                    pass
            else:
                # Non-kanji characters (24px in headers)
                if self.is_header:
                    styled_font.setPixelSize(24)
                    styled_font.setBold(True)
                else:
                    # Regular non-kanji use default size
                    pass
            
            # Calculate width using the styled font
            char_metrics = QFontMetrics(styled_font)
            char_width = char_metrics.horizontalAdvance(char)
            
            # Check if click is within this character's bounds
            if x_pos < accumulated_width + char_width:
                # Found the clicked character
                if self._is_kanji(char):
                    self.kanji_clicked.emit(char)
                return
            
            accumulated_width += char_width


class DictionaryPanel(QWidget):
    """
    Side panel for displaying dictionary entries (words or kanji).
    
    Displays:
    - Word entries: All jamdict entries with kanji/kana forms and senses
    - Kanji entries: Readings, meanings, stroke count, frequency
    - Breadcrumb trail for navigation history
    
    Signals:
    - kanji_clicked(str): Emitted when user clicks a kanji character
    - breadcrumb_clicked(int): Emitted when user clicks a breadcrumb (index)
    - closed(): Emitted when user closes the panel
    """
    
    # Signals
    kanji_clicked = Signal(str)  # kanji character
    breadcrumb_clicked = Signal(int)  # breadcrumb index
    closed = Signal()
    
    def __init__(self):
        super().__init__()
        self._breadcrumbs: List[BreadcrumbItem] = []
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Breadcrumb trail area
        self.breadcrumb_container = QWidget()
        self.breadcrumb_layout = QHBoxLayout(self.breadcrumb_container)
        self.breadcrumb_layout.setContentsMargins(0, 0, 0, 0)
        self.breadcrumb_layout.setSpacing(4)
        self.breadcrumb_layout.addStretch()
        layout.addWidget(self.breadcrumb_container)
        
        # Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(12)
        self.content_layout.addStretch()
        
        scroll_area.setWidget(self.content_widget)
        layout.addWidget(scroll_area, 1)  # Give it stretch factor
        
        # Close button
        close_button = QPushButton("Close Dictionary Panel")
        close_button.setMaximumHeight(32)
        close_button.clicked.connect(self.closed.emit)
        layout.addWidget(close_button)
    
    def display_word_entry(self, result: DictionaryLookupResult, lemma: str):
        """
        Display all word entries with clickable kanji.
        
        Args:
            result: DictionaryLookupResult with all entries
            lemma: The lemma/base form of the word
        """
        self._clear_content()
        
        if not result.entries:
            label = QLabel("No entries found")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.insertWidget(0, label)
            return
        
        for idx, entry in enumerate(result.entries, 1):
            entry_widget = self._create_word_entry_widget(entry, idx, lemma)
            self.content_layout.insertWidget(
                self.content_layout.count() - 1,  # Insert before stretch
                entry_widget
            )
    
    def display_kanji_entry(self, kanji_entry: KanjiEntry):
        """
        Display kanji entry with readings and meanings (no clickable kanji).
        
        Args:
            kanji_entry: KanjiEntry with literal, readings, meanings, etc.
        """
        self._clear_content()
        
        # Large kanji literal
        literal_label = QLabel(kanji_entry.literal)
        literal_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        literal_label.setStyleSheet("font-size: 72px; font-weight: bold; padding: 16px;")
        self.content_layout.insertWidget(0, literal_label)
        
        # Stroke count and frequency
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(8, 0, 8, 0)
        info_layout.setSpacing(4)
        
        if kanji_entry.stroke_count:
            stroke_label = QLabel(f"<b>Strokes:</b> {kanji_entry.stroke_count}")
            info_layout.addWidget(stroke_label)
        
        if kanji_entry.frequency:
            freq_label = QLabel(f"<b>Frequency:</b> {kanji_entry.frequency}")
            info_layout.addWidget(freq_label)
        
        self.content_layout.insertWidget(1, info_widget)
        
        # ON readings
        if kanji_entry.on_readings:
            on_widget = self._create_reading_widget("ON Readings (音読み)", kanji_entry.on_readings)
            self.content_layout.insertWidget(self.content_layout.count() - 1, on_widget)
        
        # KUN readings
        if kanji_entry.kun_readings:
            kun_widget = self._create_reading_widget("KUN Readings (訓読み)", kanji_entry.kun_readings)
            self.content_layout.insertWidget(self.content_layout.count() - 1, kun_widget)
        
        # Meanings
        if kanji_entry.meanings:
            meanings_widget = self._create_meanings_widget(kanji_entry.meanings)
            self.content_layout.insertWidget(self.content_layout.count() - 1, meanings_widget)
    
    def set_breadcrumbs(self, breadcrumbs: List[BreadcrumbItem]):
        """
        Update breadcrumb trail display.
        
        Args:
            breadcrumbs: List of BreadcrumbItem objects
        """
        self._breadcrumbs = breadcrumbs
        self._render_breadcrumbs()
    
    def _clear_content(self):
        """Remove all widgets from content area except stretch."""
        while self.content_layout.count() > 1:
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _create_word_entry_widget(self, entry: DictionaryEntryFull, entry_num: int, lemma: str) -> QWidget:
        """
        Create widget for a single word entry with clickable kanji in header.
        
        Args:
            entry: DictionaryEntryFull object
            entry_num: Entry number for display
            lemma: The searched lemma/word to display in header
            
        Returns:
            QWidget containing the formatted entry
        """
        entry_widget = QWidget()
        entry_layout = QVBoxLayout(entry_widget)
        entry_layout.setContentsMargins(8, 8, 8, 8)
        entry_layout.setSpacing(8)
        entry_widget.setStyleSheet("background-color: #2d2d2d; border: 1px solid #444; border-radius: 4px; color: #e0e0e0;")
        
        # Entry header with clickable kanji
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        
        # Entry number label
        entry_num_label = QLabel(f"<small style='color: #999;'>ENTRY {entry_num}</small>")
        header_layout.addWidget(entry_num_label)
        
        # Word/kanji header with clickable kanji - display SEARCHED LEMMA only
        word_header = QWidget()
        word_layout = QHBoxLayout(word_header)
        word_layout.setContentsMargins(0, 0, 0, 0)
        word_layout.setSpacing(8)
        
        # Create the main word display - showing the SEARCHED LEMMA with clickable kanji
        # Get reading from entry's kana forms if available
        reading = entry.kana_forms[0] if entry.kana_forms else ""
        kanji_header_label = self._create_clickable_kanji_header(lemma, reading)
        kanji_header_label.kanji_clicked.connect(self.kanji_clicked.emit)
        word_layout.addWidget(kanji_header_label)
        word_layout.addStretch()
        header_layout.addWidget(word_header)
        entry_layout.addWidget(header_widget)
        
        # Detailed forms section (non-clickable)
        if entry.kanji_forms or entry.kana_forms:
            forms_widget = QWidget()
            forms_layout = QVBoxLayout(forms_widget)
            forms_layout.setContentsMargins(8, 4, 8, 4)
            forms_layout.setSpacing(4)
            forms_widget.setStyleSheet("background-color: #1d1d1d; border-radius: 3px; padding: 4px;")
            
            forms_text = ""
            if entry.kanji_forms:
                forms_text += f"<b>Kanji:</b> {', '.join(entry.kanji_forms)}"
            if entry.kana_forms:
                if forms_text:
                    forms_text += "<br/>"
                forms_text += f"<b>Kana:</b> {', '.join(entry.kana_forms)}"
            
            forms_label = QLabel(forms_text)
            forms_label.setStyleSheet("color: #a0a0a0; font-size: 12px;")
            forms_layout.addWidget(forms_label)
            entry_layout.addWidget(forms_widget)
        
        # Senses (meanings)
        if entry.senses:
            senses_label = QLabel("<b>Meanings:</b>")
            entry_layout.addWidget(senses_label)
            
            for sense_idx, sense in enumerate(entry.senses, 1):
                sense_text = f"{sense_idx}. {', '.join(sense.glosses)}"
                if sense.pos:
                    sense_text += f" <i>({', '.join(sense.pos)})</i>"
                sense_label = QLabel(sense_text)
                sense_label.setWordWrap(True)
                sense_label.setStyleSheet("margin-left: 16px;")
                entry_layout.addWidget(sense_label)
        
        return entry_widget
    
    def _create_clickable_kanji_label(self, text: str) -> ClickableKanjiLabel:
        """
        Create label with clickable kanji characters.
        
        Args:
            text: String containing kanji and possibly other characters
            
        Returns:
            ClickableKanjiLabel with clickable kanji
        """
        return ClickableKanjiLabel(text, is_header=False)
    
    def _create_clickable_kanji_header(self, text: str, reading: str = "") -> ClickableKanjiLabel:
        """
        Create header label with clickable kanji characters (larger, prominent display).
        
        Args:
            text: String containing kanji and possibly other characters
            reading: Kana reading to display as furigana above the text
            
        Returns:
            ClickableKanjiLabel with clickable kanji formatted for headers
        """
        return ClickableKanjiLabel(text, is_header=True, reading=reading)
    
    
    def _is_kanji(self, char: str) -> bool:
        """
        Check if character is kanji (CJK Unified Ideographs).
        
        Args:
            char: Single character
            
        Returns:
            True if character is kanji
        """
        if not char:
            return False
        code = ord(char)
        return (
            (0x4E00 <= code <= 0x9FFF) or  # CJK Unified Ideographs
            (0x3400 <= code <= 0x4DBF) or  # CJK Extension A
            (0x20000 <= code <= 0x2A6DF) or  # CJK Extension B
            (0x2A700 <= code <= 0x2B73F) or  # CJK Extension C
            (0x2B740 <= code <= 0x2B81F) or  # CJK Extension D
            (0x2B820 <= code <= 0x2CEAF) or  # CJK Extension E
            (0xF900 <= code <= 0xFAFF) or  # CJK Compatibility Ideographs
            (0x2F800 <= code <= 0x2FA1F)  # CJK Compatibility Ideographs Supplement
        )
    
    def _create_reading_widget(self, title: str, readings: List[str]) -> QWidget:
        """
        Create widget for readings (ON or KUN).
        
        Args:
            title: Section title
            readings: List of reading strings
            
        Returns:
            QWidget with formatted readings
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        title_label = QLabel(f"<b>{title}</b>")
        layout.addWidget(title_label)
        
        for reading in readings:
            reading_label = QLabel(f"• {reading}")
            reading_label.setStyleSheet("margin-left: 16px;")
            layout.addWidget(reading_label)
        
        return widget
    
    def _create_meanings_widget(self, meanings: List[str]) -> QWidget:
        """
        Create widget for kanji meanings.
        
        Args:
            meanings: List of meaning strings
            
        Returns:
            QWidget with formatted meanings
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        title_label = QLabel("<b>Meanings</b>")
        layout.addWidget(title_label)
        
        for meaning in meanings:
            meaning_label = QLabel(f"• {meaning}")
            meaning_label.setStyleSheet("margin-left: 16px;")
            layout.addWidget(meaning_label)
        
        return widget
    
    def _render_breadcrumbs(self):
        """Render breadcrumb trail from current breadcrumb list."""
        # Clear existing breadcrumbs
        while self.breadcrumb_layout.count() > 1:  # Keep stretch
            item = self.breadcrumb_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add breadcrumb buttons
        for idx, breadcrumb in enumerate(self._breadcrumbs):
            if idx > 0:
                separator = QLabel(">")
                separator.setStyleSheet("color: #999; margin: 0 4px;")
                self.breadcrumb_layout.insertWidget(idx * 2 - 1, separator)
            
            button = QPushButton(breadcrumb.label)
            button.setFlat(True)
            button.setStyleSheet(
                "QPushButton { "
                "color: #66b3ff; "
                "text-decoration: underline; "
                "border: none; "
                "padding: 4px 8px; "
                "}"
                "QPushButton:hover { "
                "background-color: #3d3d3d; "
                "}"
            )
            button.clicked.connect(lambda checked, i=idx: self.breadcrumb_clicked.emit(i))
            self.breadcrumb_layout.insertWidget(idx * 2, button)
