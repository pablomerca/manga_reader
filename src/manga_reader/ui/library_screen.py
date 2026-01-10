"""Library screen - Grid view of manga volumes in the collection."""

from pathlib import Path
from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from manga_reader.core import LibraryVolume


class VolumeTile(QWidget):
    """A single volume tile displaying cover, title, and delete button.
    
    Signals:
        clicked: Emitted when tile (cover) is clicked with volume folder path.
        delete_requested: Emitted when delete button is clicked with volume folder path.
        title_changed: Emitted when title is edited with folder path and new title.
    """
    
    clicked = Signal(Path)
    delete_requested = Signal(Path)
    title_changed = Signal(Path, str)
    
    def __init__(self, volume: LibraryVolume, parent=None):
        super().__init__(parent)
        self.volume = volume
        self._is_editing = False
        self._original_title = volume.title
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Build the tile UI: cover image, title label, delete button."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Cover container with delete button overlay
        cover_container = QWidget()
        cover_layout = QVBoxLayout(cover_container)
        cover_layout.setContentsMargins(0, 0, 0, 0)
        
        # Cover image
        self.cover_label = QLabel()
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setStyleSheet("""
            QLabel {
                border: 2px solid #444;
                background-color: #222;
            }
            QLabel:hover {
                border: 2px solid #666;
            }
        """)
        self.cover_label.setCursor(Qt.PointingHandCursor)
        self.cover_label.mousePressEvent = self._on_cover_clicked
        
        # Load thumbnail
        if self.volume.cover_image_path.exists():
            pixmap = QPixmap(str(self.volume.cover_image_path))
            if not pixmap.isNull():
                self.cover_label.setPixmap(pixmap)
                self.cover_label.setFixedSize(pixmap.size())
            else:
                self._set_placeholder()
        else:
            self._set_placeholder()
        
        # Delete button (top-right corner)
        delete_btn = QPushButton("🗑")
        delete_btn.setFixedSize(30, 30)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(200, 50, 50, 180);
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 50, 50, 220);
            }
        """)
        delete_btn.clicked.connect(self._on_delete_clicked)
        
        # Position delete button at top-right
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(delete_btn)
        btn_layout.setContentsMargins(0, 0, 5, 0)
        
        cover_layout.addLayout(btn_layout)
        cover_layout.addWidget(self.cover_label)
        cover_layout.addStretch()
        
        layout.addWidget(cover_container)
        
        # Title (editable on double-click)
        self.title_label = QLabel(self.volume.title)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #ddd;
                font-size: 14px;
                padding: 5px;
            }
        """)
        self.title_label.mouseDoubleClickEvent = self._on_title_double_clicked
        
        self.title_edit = QLineEdit(self.volume.title)
        self.title_edit.setAlignment(Qt.AlignCenter)
        self.title_edit.setStyleSheet("""
            QLineEdit {
                color: #ddd;
                background-color: #333;
                border: 1px solid #666;
                font-size: 14px;
                padding: 5px;
            }
        """)
        self.title_edit.returnPressed.connect(self._on_title_edited)
        self.title_edit.hide()
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.title_edit)
        layout.addStretch()
    
    def _set_placeholder(self):
        """Set placeholder when cover image is unavailable."""
        self.cover_label.setText("No Cover")
        self.cover_label.setFixedSize(200, 250)
        self.cover_label.setStyleSheet("""
            QLabel {
                border: 2px solid #444;
                background-color: #222;
                color: #666;
                font-size: 16px;
            }
        """)
    
    def _on_cover_clicked(self, event):
        """Handle cover image click."""
        if not self._is_editing:
            self.clicked.emit(self.volume.folder_path)
    
    def _on_delete_clicked(self):
        """Handle delete button click."""
        self.delete_requested.emit(self.volume.folder_path)
    
    def _on_title_double_clicked(self, event):
        """Enter title edit mode."""
        if not self._is_editing:
            self._is_editing = True
            self._original_title = self.title_label.text()
            self.title_label.hide()
            self.title_edit.setText(self._original_title)
            self.title_edit.show()
            self.title_edit.setFocus()
            self.title_edit.selectAll()
    
    def _on_title_edited(self):
        """Save title changes."""
        new_title = self.title_edit.text().strip()
        if new_title and new_title != self._original_title:
            self.title_label.setText(new_title)
            self.title_changed.emit(self.volume.folder_path, new_title)
        else:
            # Revert to original
            self.title_label.setText(self._original_title)
        
        self._is_editing = False
        self.title_edit.hide()
        self.title_label.show()
    
    def keyPressEvent(self, event):
        """Handle Escape key to cancel edit."""
        if self._is_editing and event.key() == Qt.Key_Escape:
            self.title_label.setText(self._original_title)
            self._is_editing = False
            self.title_edit.hide()
            self.title_label.show()
        else:
            super().keyPressEvent(event)


class LibraryScreen(QWidget):
    """Main library screen displaying all volumes in a 3-column grid.
    
    Signals:
        volume_selected: Emitted when user clicks a volume tile (folder path).
        volume_deleted: Emitted when user confirms deletion (folder path).
        volume_title_changed: Emitted when user edits a title (folder path, new title).
    """
    
    volume_selected = Signal(Path)
    volume_deleted = Signal(Path)
    volume_title_changed = Signal(Path, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._volumes: List[LibraryVolume] = []
        self._setup_ui()
    
    def _setup_ui(self):
        """Build the library screen layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("Your Library")
        title_label.setStyleSheet("""
            QLabel {
                color: #fff;
                font-size: 24px;
                font-weight: bold;
                padding-bottom: 10px;
            }
        """)
        main_layout.addWidget(title_label)
        
        # Scroll area for grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1a1a1a;
            }
        """)
        
        # Container for grid content
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area.setWidget(self.grid_container)
        main_layout.addWidget(scroll_area)
        
        # Empty state label (hidden when volumes present)
        self.empty_label = QLabel("Please open a manga volume\nto add it to your library")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("""
            QLabel {
                color: #888;
                font-size: 18px;
                padding: 100px;
            }
        """)
        self.empty_label.hide()
        
        # Add empty label to grid (will be shown/hidden as needed)
        self.grid_layout.addWidget(self.empty_label, 0, 0, 1, 3)
    
    def display_volumes(self, volumes: List[LibraryVolume]):
        """Display the given volumes in the grid.
        
        Args:
            volumes: List of LibraryVolume entities to display.
        """
        self._volumes = volumes
        self._clear_grid()
        
        if not volumes:
            self.empty_label.show()
            return
        
        self.empty_label.hide()
        
        # Populate 3-column grid
        for idx, volume in enumerate(volumes):
            row = idx // 3
            col = idx % 3
            
            tile = VolumeTile(volume)
            tile.clicked.connect(self.volume_selected.emit)
            tile.delete_requested.connect(self._on_delete_requested)
            tile.title_changed.connect(self.volume_title_changed.emit)
            
            self.grid_layout.addWidget(tile, row, col)
    
    def _clear_grid(self):
        """Remove all tiles from the grid."""
        # Remove all widgets except empty_label
        items_to_remove = []
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            widget = item.widget()
            if widget and widget != self.empty_label:
                items_to_remove.append(widget)
        
        for widget in items_to_remove:
            self.grid_layout.removeWidget(widget)
            widget.deleteLater()
    
    def _on_delete_requested(self, folder_path: Path):
        """Show confirmation dialog before emitting delete signal."""
        # Find volume title for confirmation message
        volume_title = "this volume"
        for vol in self._volumes:
            if vol.folder_path == folder_path:
                volume_title = f"'{vol.title}'"
                break
        
        reply = QMessageBox.question(
            self,
            "Remove from Library",
            f"Remove {volume_title} from your library?\n(Files will not be deleted)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.volume_deleted.emit(folder_path)
