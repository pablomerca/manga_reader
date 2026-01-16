"""Context Sync Coordinator - scans a volume to record tracked word appearances."""

from typing import Optional, Set

from PySide6.QtCore import QObject, Signal, Slot

from manga_reader.core import MangaVolume
from manga_reader.services import MorphologyService, VocabularyService
from manga_reader.ui import MainWindow


class ContextSyncCoordinator(QObject):
    """Orchestrates volume-wide context discovery for tracked words."""

    # Signal emitted after each page is processed (current_page, total_pages)
    progress_updated = Signal(int, int)
    # Signal emitted when sync finishes (new_appearances, words_with_hits)
    sync_completed = Signal(int, int)

    def __init__(
        self,
        main_window: MainWindow,
        vocabulary_service: VocabularyService,
        morphology_service: MorphologyService,
    ) -> None:
        super().__init__()

        if main_window is None:
            raise ValueError("MainWindow must not be None")
        if vocabulary_service is None:
            raise ValueError("VocabularyService must not be None")
        if morphology_service is None:
            raise ValueError("MorphologyService must not be None")

        self._main_window = main_window
        self._vocabulary_service = vocabulary_service
        self._morphology = morphology_service
        self._current_volume: Optional[MangaVolume] = None

    def set_volume(self, volume: Optional[MangaVolume]) -> None:
        """Update the active volume context for synchronization."""
        self._current_volume = volume

    @Slot()
    def synchronize_current_volume(self) -> None:
        """Scan the current volume for tracked words and persist new appearances."""
        if self._current_volume is None:
            self._main_window.show_error(
                "No Volume Loaded",
                "Open a volume before synchronizing context appearances.",
            )
            return

        tracked_lemmas = self._vocabulary_service.get_all_tracked_lemmas()
        if not tracked_lemmas:
            self._main_window.show_info(
                "No Tracked Words",
                "Track at least one word before running context synchronization.",
            )
            return

        confirmed = self._main_window.show_question(
            "Synchronize Context",
            (
                "Scan the current volume for all appearances of your tracked words? "
                "This may take a few moments."
            ),
        )
        if not confirmed:
            return

        new_appearances = 0
        lemmas_with_hits: Set[str] = set()

        total_pages = self._current_volume.total_pages
        for page_index, page in enumerate(self._current_volume.pages):
            for block in page.ocr_blocks:
                tokens = self._morphology.tokenize(block.full_text)
                if not tokens:
                    continue

                crop_coordinates = {
                    "x": block.x,
                    "y": block.y,
                    "width": block.width,
                    "height": block.height,
                }

                for token in tokens:
                    if not token.lemma or token.lemma not in tracked_lemmas:
                        continue

                    # TODO: refactor this
                    try:
                        appearance = self._vocabulary_service.add_appearance_if_new(
                            lemma=token.lemma,
                            volume_path=self._current_volume.volume_path,
                            page_index=page_index,
                            crop_coordinates=crop_coordinates,
                            sentence_text=block.full_text,
                        )
                    except ValueError as exc:  # Fail-fast guard; should not occur
                        print(f"Context sync skipped lemma: {exc}")
                        continue

                    if appearance:
                        new_appearances += 1
                        lemmas_with_hits.add(token.lemma)

            self.progress_updated.emit(page_index + 1, total_pages)

        self.sync_completed.emit(new_appearances, len(lemmas_with_hits))

        if new_appearances == 0:
            self._main_window.show_info(
                "Context Synchronization",
                "No new context appearances were found in this volume.",
            )
            return

        self._main_window.show_info(
            "Context Synchronization Complete",
            (
                f"Found {new_appearances} new context entries "
                f"for {len(lemmas_with_hits)} tracked word(s)."
            ),
        )
