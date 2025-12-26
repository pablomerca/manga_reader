"""Main Window - Application shell with menus and toolbar."""

from pathlib import Path
from PySide6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QVBoxLayout, QWidget
from PySide6.QtCore import Signal
from PySide6.QtGui import QAction


class MainWindow(QMainWindow):
    """Provides the application shell, toolbars, and keyboard shortcut handling."""
    
    # Signal emitted when user selects a volume folder
    volume_opened = Signal(Path)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manga Reader")
        self.setGeometry(100, 100, 1200, 800)
        
        self._setup_ui()
        self._create_menu_bar()
    
    def _setup_ui(self):
        """Initialize the main UI layout."""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
    
    def _create_menu_bar(self):
        """Create the application menu bar."""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("&File")
        
        # Open Volume action
        open_action = QAction("&Open Volume...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_volume)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
    
    def _on_open_volume(self):
        """Handle the Open Volume menu action."""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Manga Volume Folder",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder_path:
            volume_path = Path(folder_path)
            
            # Check if .mokuro file exists
            mokuro_files = list(volume_path.glob("*.mokuro"))
            if not mokuro_files:
                QMessageBox.warning(
                    self,
                    "Invalid Volume",
                    f"No .mokuro file found in the selected directory:\n{volume_path}"
                )
                return
            
            # Emit signal with the selected path
            self.volume_opened.emit(volume_path)
    
    def set_canvas(self, canvas):
        """Set the manga canvas widget in the main layout."""
        self.main_layout.addWidget(canvas)
    
    def show_error(self, title: str, message: str):
        """Display an error message to the user."""
        QMessageBox.critical(self, title, message)
    
    def show_info(self, title: str, message: str):
        """Display an information message to the user."""
        QMessageBox.information(self, title, message)
