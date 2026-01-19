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

        header_layout = QHBoxLayout()
        title = QLabel("Sentence Analysis")
        title.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close_clicked.emit)
        header_layout.addWidget(close_btn)
        main_layout.addLayout(header_layout)

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
        self.translation_text.setFixedHeight(100)
        main_layout.addWidget(self.translation_text)

        self.explanation_label = QLabel("Explanation")
        self.explanation_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(self.explanation_label)

        self.explanation_text = QTextEdit()
        self.explanation_text.setReadOnly(True)
        self.explanation_text.setPlaceholderText("(Not requested yet)")
        self.explanation_text.setFixedHeight(120)
        main_layout.addWidget(self.explanation_text)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: gray;")
        main_layout.addWidget(self.status_label)
        main_layout.addStretch()

    def set_original_text(self, text: str) -> None:
        self.original_text.setPlainText(text)
        self.translation_text.clear()
        self.explanation_text.clear()
        self.status_label.clear()

    def set_translation_text(self, text: str) -> None:
        self.translation_text.setPlainText(text)

    def set_explanation_text(self, text: str) -> None:
        self.explanation_text.setPlainText(text)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def clear(self) -> None:
        self.original_text.clear()
        self.translation_text.clear()
        self.explanation_text.clear()
        self.status_label.clear()
