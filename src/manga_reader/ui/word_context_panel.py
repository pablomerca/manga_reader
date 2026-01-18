"""Word Context Panel - Displays all appearances of a tracked word."""

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from manga_reader.core import WordAppearance


class WordContextPanel(QWidget):
    """
    Panel displaying all occurrences of a tracked word across volumes.
    
    Shows a table with columns:
    - Volume Name
    - Page Number
    - Sentence Context
    
    Signals:
    - appearance_selected: emitted when user clicks on an appearance row
    - appearance_clicked_with_coords: emitted with coordinates for block highlighting
    - closed: emitted when user closes the panel
    """
    
    # Signal emitted when user selects an appearance (word_id, appearance_id, page_index)
    appearance_selected = Signal(int, int, int)
    # Signal emitted when user clicks with coordinates for highlighting (volume_id, volume_path, page_index, crop_coords_dict)
    appearance_clicked_with_coords = Signal(int, str, int, dict)
    # Signal emitted when user closes the panel
    closed = Signal()
    
    def __init__(self):
        super().__init__()
        self.current_word_id: Optional[int] = None
        self.appearances: List[WordAppearance] = []
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Create table for appearances
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Volume", "Page", "Context"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setColumnWidth(0, 120)
        self.table.setColumnWidth(1, 60)
        self.table.setColumnWidth(2, 300)
        
        # Make columns auto-resize to content
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        # Connect table signals
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table)
        
        # Create close button
        close_button = QPushButton("Close Context View")
        close_button.setMaximumHeight(32)
        close_button.clicked.connect(self.closed.emit)
        layout.addWidget(close_button)
    
    def display_word_context(self, word_id: int, word_lemma: str, 
                             appearances: List[WordAppearance]):
        """
        Display all appearances of a word.
        
        Args:
            word_id: The ID of the tracked word
            word_lemma: The lemma/base form of the word (for display)
            appearances: List of WordAppearance objects
        """
        self.current_word_id = word_id
        self.appearances = appearances
        
        # Set panel title (via setWindowTitle or parent widget title)
        self.setWindowTitle(f"Appearances of '{word_lemma}'")
        
        # Clear and populate table
        self.table.setRowCount(0)
        
        if not appearances:
            # Show empty state
            self.table.setRowCount(1)
            item = QTableWidgetItem("No occurrences found")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(0, 0, item)
            return
        
        # Add rows for each appearance
        for idx, appearance in enumerate(appearances):
            self.table.insertRow(idx)
            
            # Volume name
            volume_name = appearance.volume_name or "Unknown Volume"
            volume_item = QTableWidgetItem(volume_name)
            volume_item.setData(Qt.ItemDataRole.UserRole, idx)  # Store index for lookup
            self.table.setItem(idx, 0, volume_item)
            
            # Page number (1-indexed for display)
            page_num = appearance.page_index + 1
            page_item = QTableWidgetItem(str(page_num))
            page_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(idx, 1, page_item)
            
            # Sentence context (truncated to 60 chars)
            sentence = appearance.sentence_text
            if len(sentence) > 60:
                sentence = sentence[:57] + "..."
            context_item = QTableWidgetItem(sentence)
            self.table.setItem(idx, 2, context_item)
    
    def _on_selection_changed(self):
        """Handle when user selects a row in the table."""
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            return
        
        # Get the selected row
        row = selected_rows[0].row()
        if row < 0 or row >= len(self.appearances):
            return
        
        appearance = self.appearances[row]
        if self.current_word_id is not None:
            self.appearance_selected.emit(
                self.current_word_id,
                appearance.id,
                appearance.page_index
            )
            # Emit signal with coordinates for block highlighting
            self.appearance_clicked_with_coords.emit(
                appearance.volume_id,
                str(appearance.volume_path) if appearance.volume_path else "",
                appearance.page_index,
                appearance.crop_coordinates
            )
    
    def clear(self):
        """Clear all content from the panel."""
        self.table.setRowCount(0)
        self.current_word_id = None
        self.appearances = []
