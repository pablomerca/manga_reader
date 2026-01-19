"""Main Window - Application shell with menus and toolbar."""

from pathlib import Path
from typing import override

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QKeyEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    """Provides the application shell, toolbars, and keyboard shortcut handling."""
    
    # Signal emitted when user selects a volume folder
    volume_opened = Signal(Path)
    # Signals for page navigation
    next_page = Signal()
    previous_page = Signal()
    # Signal emitted when view mode changes
    view_mode_changed = Signal(str)  # "single" or "double"
    # Signal emitted when user wants to open vocabulary list
    open_vocabulary_requested = Signal()
    # Signal emitted when user wants to return to library
    return_to_library_requested = Signal()
    # Signal emitted when user wants to synchronize context appearances
    sync_context_requested = Signal()
    
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
        
        # Create main layout (vertical: top menu, bottom content)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create horizontal splitter for split view support
        # Left side: manga canvas, Right side: context panel (initially hidden)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_layout.addWidget(self.splitter)
        
        # Store reference to canvas container for later use
        self.canvas_container = QWidget()
        self.canvas_layout = QVBoxLayout(self.canvas_container)
        self.canvas_layout.setContentsMargins(0, 0, 0, 0)
        self.splitter.addWidget(self.canvas_container)
    
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
        
        # Return to Library action
        return_to_library_action = QAction("Return to &Library", self)
        return_to_library_action.setShortcut("Ctrl+L")
        return_to_library_action.triggered.connect(self.return_to_library_requested.emit)
        view_menu.addAction(return_to_library_action)
        
        view_menu.addSeparator()
        
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
        
        # Dictionary menu
        dictionary_menu = menu_bar.addMenu("&Dictionary")
        
        # Open Vocabulary action
        open_vocab_action = QAction("Open &Vocabulary List", self)
        open_vocab_action.setShortcut("Ctrl+V")
        open_vocab_action.triggered.connect(self._on_open_vocabulary)
        dictionary_menu.addAction(open_vocab_action)

        # Synchronize Context Appearances action
        sync_context_action = QAction("&Synchronize Context Appearances", self)
        sync_context_action.setShortcut("Ctrl+Shift+S")
        sync_context_action.triggered.connect(self.sync_context_requested.emit)
        dictionary_menu.addAction(sync_context_action)
    
    def _on_view_mode_changed(self, mode: str):
        """Handle view mode change."""
        self.view_mode_changed.emit(mode)
    
    def _on_open_vocabulary(self):
        """Handle the Open Vocabulary menu action."""
        self.open_vocabulary_requested.emit()
    
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
    
    # TODO: eliminate setter by wiring in constructor
    def set_canvas(self, canvas):
        """Set the manga canvas widget in the main layout."""
        self.canvas_layout.addWidget(canvas)
        
        # Connect canvas navigation signals (from browser/keyboard)
        # Note: Canvas emits 'next'/'prev' strings
        canvas.navigation_requested.connect(self._on_canvas_navigation)
    
    def _on_canvas_navigation(self, direction: str):
        """Handle navigation requests from the canvas."""
        if direction == "next":
            self.next_page.emit()
        elif direction == "prev":
            self.previous_page.emit()
    
    # TODO: eliminate setter 
    def set_controller(self, controller):
        """Inject the controller and wire UI signals to its slots.
        
        This keeps bootstrapping minimal while preserving dependency injection.
        The controller is expected to expose methods:
        - handle_volume_opened(Path)
        - next_page()
        - previous_page()
        - handle_view_mode_changed(str)
        - handle_open_vocabulary_list()
        - handle_sync_context_requested()
        """
        self._controller = controller
        # Signal wiring
        self.volume_opened.connect(controller.handle_volume_opened)
        self.next_page.connect(controller.next_page)
        self.previous_page.connect(controller.previous_page)
        self.view_mode_changed.connect(controller.handle_view_mode_changed)
        self.open_vocabulary_requested.connect(controller.handle_open_vocabulary_list)
        self.sync_context_requested.connect(controller.handle_sync_context_requested)
    
    def show_error(self, title: str, message: str):
        """Display an error message to the user."""
        QMessageBox.critical(self, title, message)
    
    def show_info(self, title: str, message: str):
        """Display an information message to the user."""
        QMessageBox.information(self, title, message)
    
    def show_question(self, title: str, message: str) -> bool:
        """
        Display a question dialog with Yes/No buttons.
        
        Returns:
            True if user clicked Yes, False if user clicked No or closed dialog
        """
        reply = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes
    
    def show_relocation_dialog(self, volume_title: str, old_path: Path) -> Path:
        """Display error and prompt user to relocate a volume.
        
        Args:
            volume_title: The title of the volume that couldn't be found.
            old_path: The invalid path that was stored.
            
        Returns:
            Path: The new valid folder path selected by user.
            
        Raises:
            RuntimeError: If user cancels or selects invalid path.
        """
        # Show error message with relocation option
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("Volume Not Found")
        msg_box.setText(f"The volume '{volume_title}' could not be found at:")
        msg_box.setInformativeText(str(old_path))
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Ok
        )
        relocate_btn = msg_box.button(QMessageBox.StandardButton.Ok)
        relocate_btn.setText("Relocate...")
        msg_box.setDefaultButton(relocate_btn)
        
        result = msg_box.exec()
        
        if result != QMessageBox.StandardButton.Ok:
            raise RuntimeError("Relocation cancelled by user")
        
        # Open folder selection dialog
        new_folder = QFileDialog.getExistingDirectory(
            self,
            "Select New Volume Location",
            str(old_path.parent) if old_path.parent.exists() else "",
            QFileDialog.Option.ShowDirsOnly,
        )
        
        if not new_folder:
            raise RuntimeError("No folder selected")
        
        new_path = Path(new_folder)
        
        # Validate that the new path has a .mokuro file
        mokuro_files = list(new_path.glob("*.mokuro"))
        if not mokuro_files:
            raise RuntimeError(
                f"No .mokuro file found in the selected directory:\n{new_path}"
            )
        
        return new_path
    
    def set_context_panel(self, context_panel):
        """
        Set the word context panel and add it to the split view.
        
        Args:
            context_panel: WordContextPanel widget instance
        """
        self.context_panel = context_panel
        self.splitter.addWidget(context_panel)
        # Start with context panel hidden
        self.context_panel.hide()
        # Set initial splitter sizes (80/20 split when context is visible)
        self.splitter.setSizes([800, 200])

    def set_sentence_panel(self, sentence_panel):
        """Set the sentence analysis panel and add it to the split view."""
        self.sentence_panel = sentence_panel
        self.splitter.addWidget(sentence_panel)
        self.sentence_panel.hide()
        # Default splitter sizes when sentence panel is shown alongside canvas
        self.splitter.setSizes([700, 200, 200])
    
    def show_context_panel(self):
        """Show the context panel and adjust splitter."""
        if self.context_panel:
            self.context_panel.show()
            # Adjust splitter to show both panes (70/30 split)
            self.splitter.setSizes([700, 300])
    
    def hide_context_panel(self):
        """Hide the context panel."""
        if self.context_panel:
            self.context_panel.hide()
            # Reset splitter to full canvas
            self.splitter.setSizes([1000, 0])

    def show_sentence_panel(self):
        """Show the sentence analysis panel and adjust splitter for three panes."""
        if hasattr(self, "sentence_panel") and self.sentence_panel:
            self.sentence_panel.show()
            # If context panel also exists, keep it visible; otherwise split between two
            visible_widgets = [self.splitter.widget(i) for i in range(self.splitter.count()) if self.splitter.widget(i) and self.splitter.widget(i).isVisible()]
            if len(visible_widgets) == 3:
                self.splitter.setSizes([600, 200, 200])
            else:
                # Allocate space to canvas (index 0) and sentence panel (index 2)
                self.splitter.setSizes([700, 0, 300])

    def hide_sentence_panel(self):
        """Hide the sentence analysis panel."""
        if hasattr(self, "sentence_panel") and self.sentence_panel:
            self.sentence_panel.hide()
            # Prefer two-pane layout if context panel is visible, else canvas full width
            if hasattr(self, "context_panel") and self.context_panel and self.context_panel.isVisible():
                self.splitter.setSizes([700, 300, 0])
            else:
                self.splitter.setSizes([1000, 0, 0])
    
    def display_library_view(self, library_screen):
        """Switch to library screen view.
        
        Args:
            library_screen: LibraryScreen widget to display.
        """
        # Clear canvas container and add library screen
        while self.canvas_layout.count():
            item = self.canvas_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
        
        self.canvas_layout.addWidget(library_screen)
        library_screen.show()
        self.setWindowTitle("Manga Reader - Library")
    
    def display_reading_view(self, canvas):
        """Switch back to reading view.
        
        Args:
            canvas: MangaCanvas widget to display.
        """
        # Clear canvas container and add canvas
        while self.canvas_layout.count():
            item = self.canvas_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
        
        self.canvas_layout.addWidget(canvas)
        canvas.show()
        self.setWindowTitle("Manga Reader")
    
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
