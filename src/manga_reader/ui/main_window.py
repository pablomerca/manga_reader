"""Main Window - Application shell with menus and toolbar."""

from pathlib import Path
from typing import override
from PySide6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QVBoxLayout, QWidget
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QAction, QKeyEvent, QActionGroup


class MainWindow(QMainWindow):
    """Provides the application shell, toolbars, and keyboard shortcut handling."""
    
    # Signal emitted when user selects a volume folder
    volume_opened = Signal(Path)
    # Signals for page navigation
    next_page = Signal()
    previous_page = Signal()
    # Signal emitted when view mode changes
    view_mode_changed = Signal(str)  # "single" or "double"
    
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
        
        # View menu
        view_menu = menu_bar.addMenu("&View")
        
        # Create action group for exclusive selection
        view_mode_group = QActionGroup(self)
        view_mode_group.setExclusive(True)
        
        # Single Page action
        single_page_action = QAction("&Single Page", self)
        single_page_action.setCheckable(True)
        single_page_action.setChecked(True)  # Default
        single_page_action.triggered.connect(lambda: self._on_view_mode_changed("single"))
        view_mode_group.addAction(single_page_action)
        view_menu.addAction(single_page_action)
        
        # Double Page action
        double_page_action = QAction("&Double Page", self)
        double_page_action.setCheckable(True)
        double_page_action.triggered.connect(lambda: self._on_view_mode_changed("double"))
        view_mode_group.addAction(double_page_action)
        view_menu.addAction(double_page_action)
    
    def _on_view_mode_changed(self, mode: str):
        """Handle view mode change."""
        self.view_mode_changed.emit(mode)
    
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
    
    def set_controller(self, controller):
        """Inject the controller and wire UI signals to its slots.
        
        This keeps bootstrapping minimal while preserving dependency injection.
        The controller is expected to expose methods:
        - handle_volume_opened(Path)
        - next_page()
        - previous_page()
        - handle_view_mode_changed(str)
        """
        self._controller = controller
        # Signal wiring
        self.volume_opened.connect(controller.handle_volume_opened)
        self.next_page.connect(controller.next_page)
        self.previous_page.connect(controller.previous_page)
        self.view_mode_changed.connect(controller.handle_view_mode_changed)
    
    def show_error(self, title: str, message: str):
        """Display an error message to the user."""
        QMessageBox.critical(self, title, message)
    
    def show_info(self, title: str, message: str):
        """Display an information message to the user."""
        QMessageBox.information(self, title, message)
    
    @override   
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard events for navigation.
        
        Japanese manga reading order (right-to-left):
        - Left arrow: Next page (moving forward in story)
        - Right arrow: Previous page (going back in story)
        """
        if event.key() == Qt.Key.Key_Left:
            self.next_page.emit()
        elif event.key() == Qt.Key.Key_Right:
            self.previous_page.emit()
        else:
            # Pass other keys to parent
            super().keyPressEvent(event)
