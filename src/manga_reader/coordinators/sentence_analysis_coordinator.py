"""Sentence Analysis Coordinator - Manages translate/explain workflow and panel state."""

from datetime import datetime
from typing import Optional

from PySide6.QtCore import QObject, QThreadPool, Signal, Slot

from manga_reader.services import (
    CacheRecord,
    ExplanationService,
    SettingsManager,
    TranslationCache,
    TranslationService,
    normalize_text,
)
from manga_reader.services.api_workers import TranslationWorker, ExplanationWorker
from manga_reader.ui import MainWindow


class _TranslationRequest(QObject):
    """Helper class to hold translation request context and handle results safely."""
    
    def __init__(self, normalized: str, worker_id: int, parent: "SentenceAnalysisCoordinator"):
        super().__init__()
        self.normalized = normalized
        self.worker_id = worker_id
        self.parent_ref = parent
    
    @Slot(object)
    def on_translation_result(self, result):
        """Handle translation result safely."""
        coordinator = self.parent_ref
        if coordinator:
            try:
                coordinator._handle_translation_result(result, self.normalized, self.worker_id)
            except RuntimeError:
                # Coordinator might be destroyed, ignore
                pass
    
    @Slot(str)
    def on_translation_error(self, error: str):
        """Handle translation error safely."""
        coordinator = self.parent_ref
        if coordinator:
            try:
                coordinator._handle_translation_error(error, self.worker_id)
            except RuntimeError:
                # Coordinator might be destroyed, ignore
                pass


class _ExplanationRequest(QObject):
    """Helper class to hold explanation request context and handle results safely."""
    
    def __init__(
        self,
        normalized: str,
        worker_id: int,
        translation_text: str,
        translation_model: str,
        cached,
        parent: "SentenceAnalysisCoordinator",
    ):
        super().__init__()
        self.normalized = normalized
        self.worker_id = worker_id
        self.translation_text = translation_text
        self.translation_model = translation_model
        self.cached = cached
        self.parent_ref = parent
    
    @Slot(object)
    def on_explanation_result(self, result):
        """Handle explanation result safely."""
        coordinator = self.parent_ref
        if coordinator:
            try:
                coordinator._handle_explanation_result(
                    result,
                    self.normalized,
                    self.translation_text,
                    self.translation_model,
                    self.cached,
                    self.worker_id,
                )
            except RuntimeError:
                pass
    
    @Slot(str)
    def on_explanation_error(self, error: str):
        """Handle explanation error safely."""
        coordinator = self.parent_ref
        if coordinator:
            try:
                coordinator._handle_explanation_error(error, self.cached, self.worker_id)
            except RuntimeError:
                pass


class _ExplanationTranslationRequest(QObject):
    """Helper class to hold explanation translation request context."""
    
    def __init__(
        self,
        normalized: str,
        cached,
        api_key: str,
        worker_id: int,
        parent: "SentenceAnalysisCoordinator",
    ):
        super().__init__()
        self.normalized = normalized
        self.cached = cached
        self.api_key = api_key
        self.worker_id = worker_id
        self.parent_ref = parent
    
    @Slot(object)
    def on_translation_result(self, result):
        """Handle translation result for explanation workflow."""
        coordinator = self.parent_ref
        if coordinator:
            try:
                coordinator._handle_translation_for_explanation(
                    result, self.normalized, self.cached, self.api_key, self.worker_id
                )
            except RuntimeError:
                pass
    
    @Slot(str)
    def on_translation_error(self, error: str):
        """Handle translation error for explanation workflow."""
        coordinator = self.parent_ref
        if coordinator:
            try:
                coordinator._handle_explanation_translation_error(error, self.cached, self.worker_id)
            except RuntimeError:
                pass


class SentenceAnalysisCoordinator(QObject):
    """
    Orchestrates the sentence analysis/translation workflow.

    Responsibilities:
    - Manage panel state (selected block text, actions enabled/disabled based on API key).
    - Handle translate and explain action requests.
    - Coordinate cache lookups and API calls via services.
    - Update panel UI with results, errors, loading states.
    """

    block_selected = Signal(str)
    translation_requested = Signal(str)
    explanation_requested = Signal(str)
    panel_closed = Signal()
    
    translation_started = Signal()
    translation_completed = Signal(str)
    translation_failed = Signal(str)
    explanation_started = Signal()
    explanation_completed = Signal(str)
    explanation_failed = Signal(str)
    explanation_loading = Signal(str)

    def __init__(
        self,
        main_window: MainWindow,
        translation_cache: TranslationCache,
        translation_service: TranslationService,
        explanation_service: ExplanationService,
        settings_manager: SettingsManager,
    ):
        super().__init__()

        self.main_window = main_window
        self.translation_cache = translation_cache
        self.translation_service = translation_service
        self.explanation_service = explanation_service
        self.settings_manager = settings_manager

        self.selected_block_text: Optional[str] = None
        self.current_volume_id: Optional[str] = None
        
        # Thread pool for async API calls
        self.thread_pool = QThreadPool.globalInstance()
        print(f"Thread pool max threads: {self.thread_pool.maxThreadCount()}")
        
        # Track active workers to prevent race conditions
        # When state changes, we invalidate old workers so they don't update stale state
        self._active_translation_worker_id: Optional[int] = None
        self._active_explanation_worker_id: Optional[int] = None
        self._worker_counter = 0  # Unique ID for each worker request
        
        # Keep references to helper objects so they don't get garbage collected
        # while workers are running in background threads
        self._translation_request_helper: Optional[_TranslationRequest] = None
        self._explanation_request_helper: Optional[_ExplanationRequest] = None
        self._explanation_translation_request_helper: Optional[_ExplanationTranslationRequest] = None


    def on_block_selected(self, block_text: str, volume_id: str) -> None:
        """
        Called when user clicks an OCR block.

        Args:
            block_text: Original Japanese text from the block.
            volume_id: Current volume identifier (for cache keying).
        """
        # Invalidate any pending workers when block selection changes
        # This prevents stale workers from updating UI with old data
        self._active_translation_worker_id = None
        self._active_explanation_worker_id = None
        
        self.selected_block_text = block_text
        self.current_volume_id = volume_id
        self.block_selected.emit(block_text)

    def request_translation(self) -> None:
        """Request translation of the currently selected block."""
        if not self.selected_block_text:
            self.main_window.show_error("No block selected")
            return
        
        api_key = self._current_api_key()
        if not api_key:
            self.main_window.show_error("API key not configured. Add GEMINI_API_KEY to .env file.")
            return

        if not self.current_volume_id:
            self.main_window.show_error("No volume loaded")
            return

        self.translation_started.emit()
        
        normalized = normalize_text(self.selected_block_text)
        
        cached = self.translation_cache.get(
            volume_id=self.current_volume_id,
            normalized_text=normalized,
            lang="en"
        )
        
        if cached and cached.translation:
            self.translation_completed.emit(cached.translation)
            return
        
        # Generate unique ID for this worker to detect stale completions
        self._worker_counter += 1
        worker_id = self._worker_counter
        self._active_translation_worker_id = worker_id
        
        # Run API call in background thread
        worker = TranslationWorker(
            translation_service=self.translation_service,
            text=self.selected_block_text,
            api_key=api_key,
        )
        
        # Use helper object to manage signal connections safely
        # IMPORTANT: Store reference so it doesn't get garbage collected while worker runs
        request_helper = _TranslationRequest(normalized, worker_id, self)
        self._translation_request_helper = request_helper
        
        worker.signals.translation_result.connect(request_helper.on_translation_result)
        worker.signals.error.connect(request_helper.on_translation_error)
        
        # Start the worker
        self.thread_pool.start(worker)

    def _handle_translation_result(self, result, normalized: str, worker_id: int) -> None:
        """
        Handle translation result from worker thread (runs in main thread).
        
        Args:
            result: Translation result object
            normalized: Normalized text for caching
            worker_id: ID of the worker that produced this result
        """
        # Ignore results from stale workers (user may have navigated or selected different block)
        if worker_id != self._active_translation_worker_id:
            print(f"DEBUG: Ignoring stale translation result (worker {worker_id}, current {self._active_translation_worker_id})")
            return
        
        if result.is_error:
            self.translation_failed.emit(result.error or "Unknown error")
            return
        
        record = CacheRecord(
            normalized_text=normalized,
            lang="en",
            translation=result.text,
            explanation=None,
            model=result.model,
            updated_at=datetime.now(),
        )
        
        self.translation_cache.put(
            volume_id=self.current_volume_id,
            normalized_text=normalized,
            lang="en",
            record=record,
        )
        
        self.translation_completed.emit(result.text)

    def _handle_translation_error(self, error: str, worker_id: int) -> None:
        """
        Handle translation error from worker thread.
        
        Args:
            error: Error message
            worker_id: ID of the worker that produced this error
        """
        # Ignore errors from stale workers
        if worker_id != self._active_translation_worker_id:
            print(f"DEBUG: Ignoring stale translation error (worker {worker_id}, current {self._active_translation_worker_id})")
            return
        
        self.translation_failed.emit(error)

    def request_explanation(self) -> None:
        """Request explanation of the currently selected block with translation fallback."""
        if not self.selected_block_text:
            self.main_window.show_error("No block selected")
            return

        api_key = self._current_api_key()
        if not api_key:
            self.main_window.show_error("API key not configured")
            return

        if not self.current_volume_id:
            self.main_window.show_error("No volume loaded")
            return

        self.explanation_requested.emit(self.selected_block_text)
        self.explanation_started.emit()
        normalized = normalize_text(self.selected_block_text)
        
        # Generate unique ID for this explanation request sequence
        self._worker_counter += 1
        worker_id = self._worker_counter
        self._active_explanation_worker_id = worker_id

        cached = self.translation_cache.get(
            volume_id=self.current_volume_id,
            normalized_text=normalized,
            lang="en",
        )

        if cached and cached.explanation:
            if cached.translation:
                self.translation_completed.emit(cached.translation)
            self.explanation_completed.emit(cached.explanation)
            return

        translation_text = cached.translation if cached else None
        translation_model = cached.model if cached else ""

        if not translation_text:
            # Need to fetch translation first, then explanation
            self.explanation_loading.emit("Fetching translation...")
            self._request_translation_for_explanation(
                api_key=api_key,
                normalized=normalized,
                cached=cached,
                worker_id=worker_id,
            )
        else:
            # Already have translation, go straight to explanation
            if cached.translation:
                self.translation_completed.emit(cached.translation)
            
            self.explanation_loading.emit("Analyzing...")
            self._request_explanation_with_translation(
                api_key=api_key,
                normalized=normalized,
                translation_text=translation_text,
                translation_model=translation_model,
                cached=cached,
                worker_id=worker_id,
            )

    def _request_translation_for_explanation(
        self, api_key: str, normalized: str, cached, worker_id: int
    ) -> None:
        """Request translation as first step before explanation (async)."""
        worker = TranslationWorker(
            translation_service=self.translation_service,
            text=self.selected_block_text,
            api_key=api_key,
        )

        # Use helper object to manage signal connections safely
        # IMPORTANT: Store reference so it doesn't get garbage collected while worker runs
        request_helper = _ExplanationTranslationRequest(normalized, cached, api_key, worker_id, self)
        self._explanation_translation_request_helper = request_helper
        
        worker.signals.translation_result.connect(request_helper.on_translation_result)
        worker.signals.error.connect(request_helper.on_translation_error)

        # Start the worker
        self.thread_pool.start(worker)

    def _handle_translation_for_explanation(
        self, result, normalized: str, cached, api_key: str, worker_id: int
    ) -> None:
        """Handle translation result when it's part of explanation workflow."""
        # Ignore results from stale workers
        if worker_id != self._active_explanation_worker_id:
            print(f"DEBUG: Ignoring stale explanation translation result (worker {worker_id}, current {self._active_explanation_worker_id})")
            return
        
        if result.is_error:
            if cached and cached.explanation:
                self.explanation_completed.emit(f"{cached.explanation}\n\n(cached)")
            else:
                self.explanation_failed.emit(result.error or "Unknown error")
            return

        translation_text = result.text
        translation_model = result.model

        # Store translation in cache
        record = CacheRecord(
            normalized_text=normalized,
            lang="en",
            translation=translation_text,
            explanation=cached.explanation if cached else None,
            model=translation_model,
            updated_at=datetime.now(),
        )

        self.translation_cache.put(
            volume_id=self.current_volume_id,
            normalized_text=normalized,
            lang="en",
            record=record,
        )

        # Emit translation to UI
        self.translation_completed.emit(translation_text)

        # Now request explanation with the translation
        self.explanation_loading.emit("Analyzing...")
        self._request_explanation_with_translation(
            api_key=api_key,
            normalized=normalized,
            translation_text=translation_text,
            translation_model=translation_model,
            cached=cached,
            worker_id=worker_id,
        )

    def _handle_explanation_translation_error(self, error: str, cached, worker_id: int) -> None:
        """Handle error when fetching translation for explanation."""
        # Ignore errors from stale workers
        if worker_id != self._active_explanation_worker_id:
            print(f"DEBUG: Ignoring stale explanation translation error (worker {worker_id}, current {self._active_explanation_worker_id})")
            return
        
        if cached and cached.explanation:
            self.explanation_completed.emit(f"{cached.explanation}\n\n(cached)")
        else:
            self.explanation_failed.emit(error)

    def _request_explanation_with_translation(
        self,
        api_key: str,
        normalized: str,
        translation_text: str,
        translation_model: str,
        cached,
        worker_id: int,
    ) -> None:
        """Request explanation with translation already available (async)."""
        worker = ExplanationWorker(
            explanation_service=self.explanation_service,
            original_jp=self.selected_block_text,
            translation_en=translation_text,
            api_key=api_key,
        )

        # Use helper object to manage signal connections safely
        # IMPORTANT: Store reference so it doesn't get garbage collected while worker runs
        request_helper = _ExplanationRequest(
            normalized, worker_id, translation_text, translation_model, cached, self
        )
        self._explanation_request_helper = request_helper
        
        worker.signals.explanation_result.connect(request_helper.on_explanation_result)
        worker.signals.error.connect(request_helper.on_explanation_error)

        # Start the worker
        self.thread_pool.start(worker)

    def _handle_explanation_result(
        self,
        result,
        normalized: str,
        translation_text: str,
        translation_model: str,
        cached,
        worker_id: int,
    ) -> None:
        """Handle explanation result from worker thread (runs in main thread)."""
        # Ignore results from stale workers
        if worker_id != self._active_explanation_worker_id:
            print(f"DEBUG: Ignoring stale explanation result (worker {worker_id}, current {self._active_explanation_worker_id})")
            return
        
        if not result.is_success():
            if cached and cached.explanation:
                self.explanation_completed.emit(f"{cached.explanation}\n\n(cached)")
            else:
                self.explanation_failed.emit(result.error or "Unknown error")
            return

        record_to_store = CacheRecord(
            normalized_text=normalized,
            lang="en",
            translation=translation_text,
            explanation=result.text,
            model=result.model or translation_model,
            updated_at=datetime.now(),
        )

        self.translation_cache.put(
            volume_id=self.current_volume_id,
            normalized_text=normalized,
            lang="en",
            record=record_to_store,
        )

        self.explanation_completed.emit(result.text)

    def _handle_explanation_error(self, error: str, cached, worker_id: int) -> None:
        """Handle error from explanation worker."""
        # Ignore errors from stale workers
        if worker_id != self._active_explanation_worker_id:
            print(f"DEBUG: Ignoring stale explanation error (worker {worker_id}, current {self._active_explanation_worker_id})")
            return
        
        if cached and cached.explanation:
            self.explanation_completed.emit(f"{cached.explanation}\n\n(cached)")
        else:
            self.explanation_failed.emit(error)

    def on_panel_closed(self) -> None:
        """Called when user closes the panel."""
        # Invalidate any pending workers when panel closes
        self._active_translation_worker_id = None
        self._active_explanation_worker_id = None
        
        self.selected_block_text = None
        self.panel_closed.emit()

    def actions_enabled(self) -> bool:
        """Return True if translation/explanation actions should be enabled."""
        return bool(self._current_api_key()) and self.selected_block_text is not None

    def _current_api_key(self) -> Optional[str]:
        """Fetch the latest API key from settings."""
        return self.settings_manager.get_gemini_api_key()
