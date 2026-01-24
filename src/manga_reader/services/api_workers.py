"""Async workers for non-blocking API calls using Qt threading."""

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from manga_reader.services.translation_service import TranslationService, TranslationResult
from manga_reader.services.explanation_service import ExplanationService, ExplanationResult


class WorkerSignals(QObject):
    """
    Signals for communicating results from worker threads.
    
    QRunnable doesn't inherit from QObject, so we need a separate
    QObject to hold the signals.
    """
    finished = Signal()
    error = Signal(str)
    translation_result = Signal(object)  # TranslationResult
    explanation_result = Signal(object)  # ExplanationResult


class TranslationWorker(QRunnable):
    """
    Worker that runs translation API call in a background thread.
    
    Uses Qt's thread pool for efficient thread management.
    Emits signals when translation completes or fails.
    """

    def __init__(
        self,
        translation_service: TranslationService,
        text: str,
        api_key: str,
    ):
        super().__init__()
        self.translation_service = translation_service
        self.text = text
        self.api_key = api_key
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        """Execute the translation API call in background thread."""
        try:
            result = self.translation_service.translate(
                text=self.text,
                api_key=self.api_key,
            )
            self.signals.translation_result.emit(result)
        except Exception as e:
            # Catch any unexpected exceptions not handled by service
            self.signals.error.emit(f"Unexpected translation error: {str(e)}")
        finally:
            self.signals.finished.emit()


class ExplanationWorker(QRunnable):
    """
    Worker that runs explanation API call in a background thread.
    
    Uses Qt's thread pool for efficient thread management.
    Emits signals when explanation completes or fails.
    """

    def __init__(
        self,
        explanation_service: ExplanationService,
        original_jp: str,
        translation_en: str,
        api_key: str,
    ):
        super().__init__()
        self.explanation_service = explanation_service
        self.original_jp = original_jp
        self.translation_en = translation_en
        self.api_key = api_key
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        """Execute the explanation API call in background thread."""
        try:
            result = self.explanation_service.explain(
                original_jp=self.original_jp,
                translation_en=self.translation_en,
                api_key=self.api_key,
            )
            self.signals.explanation_result.emit(result)
        except Exception as e:
            # Catch any unexpected exceptions not handled by service
            self.signals.error.emit(f"Unexpected explanation error: {str(e)}")
        finally:
            self.signals.finished.emit()
