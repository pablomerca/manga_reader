"""Sentence Analysis Panel - UI scaffold for translation/explanation actions."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QTextEdit,
    QSizePolicy,
)


class SentenceAnalysisPanel(QWidget):
    """Side panel that shows selected text and action buttons."""

    translate_clicked = Signal()
    explain_clicked = Signal()
    close_clicked = Signal()

    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        title = QLabel("Sentence Analysis")
        title.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(title)

        self.original_label = QLabel("Original")
        self.original_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(self.original_label)

        self.original_text = QTextEdit()
        self.original_text.setReadOnly(True)
        self.original_text.setPlaceholderText("Select a block to view its text")
        self.original_text.setFixedHeight(120)
        main_layout.addWidget(self.original_text)

        actions_layout = QHBoxLayout()
        self.translate_button = QPushButton("Translate")
        self.translate_button.clicked.connect(self.translate_clicked.emit)
        self.explain_button = QPushButton("Explain")
        self.explain_button.clicked.connect(self.explain_clicked.emit)
        actions_layout.addWidget(self.translate_button)
        actions_layout.addWidget(self.explain_button)
        actions_layout.addStretch()
        main_layout.addLayout(actions_layout)

        self.translation_label = QLabel("Translation")
        self.translation_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(self.translation_label)

        self.translation_text = QTextEdit()
        self.translation_text.setReadOnly(True)
        self.translation_text.setPlaceholderText("(Not requested yet)")
        self.translation_text.setMinimumHeight(140)
        self.translation_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self.translation_text, 1)

        self.explanation_label = QLabel("Explanation")
        self.explanation_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(self.explanation_label)

        self.explanation_text = QTextEdit()
        self.explanation_text.setReadOnly(True)
        self.explanation_text.setPlaceholderText("(Not requested yet)")
        self.explanation_text.setMinimumHeight(200)
        self.explanation_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self.explanation_text, 2)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: gray;")
        main_layout.addWidget(self.status_label)
        main_layout.addStretch()

        # Close button at the bottom for consistency with context panel
        close_btn = QPushButton("Close")
        close_btn.setMaximumHeight(32)
        close_btn.clicked.connect(self.close_clicked.emit)
        main_layout.addWidget(close_btn)

    def set_original_text(self, text: str) -> None:
        self.original_text.setPlainText(text)
        self.translation_text.clear()
        self.explanation_text.clear()
        self.status_label.clear()
        self.translate_button.setEnabled(True)
        self.translate_button.setText("Translate")
        self.explain_button.setEnabled(True)
        self.explain_button.setText("Explain")

    def set_translation_text(self, text: str) -> None:
        self.translation_text.setPlainText(text)

    def set_explanation_text(self, text: str) -> None:
        self.explanation_text.setPlainText(text)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)
    
    def show_translation_loading(self) -> None:
        """Show loading state for translation."""
        self.translation_text.setPlaceholderText("Translating...")
        self.translate_button.setEnabled(False)
        self.status_label.setText("Loading...")
    
    def show_translation_error(self, error: str) -> None:
        """Show error state for translation."""
        self.translation_text.setPlainText(f"Error: {error}")
        self.translate_button.setEnabled(True)
        self.translate_button.setText("Retry")
        self.status_label.setText("Failed")
        self.status_label.setStyleSheet("color: red;")
    
    def show_translation_success(self, text: str) -> None:
        """Show success state with translated text."""
        self.translation_text.setPlainText(text)
        self.translate_button.setEnabled(True)
        self.translate_button.setText("Translate")
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("color: gray;")

    def show_explanation_loading(self, message: str) -> None:
        """Show loading state for explanation requests."""
        self.explanation_text.clear()
        self.explanation_text.setPlaceholderText(message)
        self.explain_button.setEnabled(False)
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: gray;")

    def show_explanation_error(self, error: str) -> None:
        """Show error state for explanations with retry affordance."""
        self.explanation_text.setPlainText(f"Error: {error}")
        self.explain_button.setEnabled(True)
        self.explain_button.setText("Retry")
        self.status_label.setText("Failed")
        self.status_label.setStyleSheet("color: red;")

    def show_explanation_success(self, text: str) -> None:
        """Show successful explanation text."""
        self.explanation_text.setPlainText(text)
        self.explain_button.setEnabled(True)
        self.explain_button.setText("Explain")
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("color: gray;")

    def clear(self) -> None:
        self.original_text.clear()
        self.translation_text.clear()
        self.explanation_text.clear()
        self.status_label.clear()
        self.translate_button.setEnabled(True)
        self.translate_button.setText("Translate")
        self.explain_button.setEnabled(True)
        self.explain_button.setText("Explain")
        self.status_label.setStyleSheet("color: gray;")
