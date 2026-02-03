"""Dictionary Side Panel - Displays full word/kanji entries with clickable kanji."""

from typing import List

from PySide6.QtCore import Qt, Signal
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
            entry_widget = self._create_word_entry_widget(entry, idx)
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
    
    def _create_word_entry_widget(self, entry: DictionaryEntryFull, entry_num: int) -> QWidget:
        """
        Create widget for a single word entry with clickable kanji.
        
        Args:
            entry: DictionaryEntryFull object
            entry_num: Entry number for display
            
        Returns:
            QWidget containing the formatted entry
        """
        entry_widget = QWidget()
        entry_layout = QVBoxLayout(entry_widget)
        entry_layout.setContentsMargins(8, 8, 8, 8)
        entry_layout.setSpacing(6)
        entry_widget.setStyleSheet("background-color: #f9f9f9; border: 1px solid #ddd; border-radius: 4px;")
        
        # Entry header
        header_label = QLabel(f"<b>Entry {entry_num}</b>")
        if entry.entry_id:
            header_label.setText(f"<b>Entry {entry_num}</b> <small>(ID: {entry.entry_id})</small>")
        entry_layout.addWidget(header_label)
        
        # Kanji and kana forms
        forms_widget = QWidget()
        forms_layout = QHBoxLayout(forms_widget)
        forms_layout.setContentsMargins(0, 0, 0, 0)
        forms_layout.setSpacing(8)
        
        if entry.kanji_forms:
            kanji_label = QLabel("Kanji:")
            kanji_label.setStyleSheet("font-weight: bold;")
            forms_layout.addWidget(kanji_label)
            
            # Create clickable kanji labels
            for kanji_form in entry.kanji_forms:
                kanji_widget = self._create_clickable_kanji_label(kanji_form)
                forms_layout.addWidget(kanji_widget)
        
        if entry.kana_forms:
            kana_label = QLabel("Kana:")
            kana_label.setStyleSheet("font-weight: bold; margin-left: 8px;")
            forms_layout.addWidget(kana_label)
            
            kana_text = ", ".join(entry.kana_forms)
            kana_value = QLabel(kana_text)
            forms_layout.addWidget(kana_value)
        
        forms_layout.addStretch()
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
    
    def _create_clickable_kanji_label(self, text: str) -> QLabel:
        """
        Create label with clickable kanji characters.
        
        Args:
            text: String containing kanji and possibly other characters
            
        Returns:
            QLabel with clickable kanji
        """
        label = QLabel()
        html_parts = []
        
        for char in text:
            if self._is_kanji(char):
                # Make kanji clickable with hover effect
                html_parts.append(
                    f'<span style="color: #0066cc; cursor: pointer; text-decoration: underline;" '
                    f'onclick="window.kanji_clicked(\'{char}\')">{char}</span>'
                )
            else:
                html_parts.append(char)
        
        label.setText(''.join(html_parts))
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        label.linkActivated.connect(lambda: None)  # Prevent default link handling
        
        # Connect click events (we'll handle this via mouse events)
        label.mousePressEvent = lambda event: self._handle_kanji_click(text, event)
        
        return label
    
    def _handle_kanji_click(self, text: str, event):
        """
        Handle click on kanji label - determine which kanji was clicked.
        
        Args:
            text: The full text of the label
            event: Mouse event
        """
        # For simplicity, emit the first kanji found
        # A more sophisticated approach would calculate click position
        for char in text:
            if self._is_kanji(char):
                self.kanji_clicked.emit(char)
                break
    
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
                separator.setStyleSheet("color: #888; margin: 0 4px;")
                self.breadcrumb_layout.insertWidget(idx * 2 - 1, separator)
            
            button = QPushButton(breadcrumb.label)
            button.setFlat(True)
            button.setStyleSheet(
                "QPushButton { "
                "color: #0066cc; "
                "text-decoration: underline; "
                "border: none; "
                "padding: 4px 8px; "
                "}"
                "QPushButton:hover { "
                "background-color: #f0f0f0; "
                "}"
            )
            button.clicked.connect(lambda checked, i=idx: self.breadcrumb_clicked.emit(i))
            self.breadcrumb_layout.insertWidget(idx * 2, button)
