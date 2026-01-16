"""Word Interaction Coordinator - Handles word clicks and vocabulary tracking."""

from typing import Optional

from PySide6.QtCore import QObject, Slot

from manga_reader.core import MangaVolume
from manga_reader.services import DictionaryService, VocabularyService
from manga_reader.ui import MainWindow, MangaCanvas


class WordInteractionCoordinator(QObject):
    """
    Manages the word click → dictionary lookup → tracking workflow.

    Responsibilities:
    - Handle word clicks from canvas
    - Show dictionary popup
    - Track words to vocabulary
    - Provide page/block context for tracking
    """

    def __init__(
        self,
        canvas: MangaCanvas,
        dictionary_service: DictionaryService,
        vocabulary_service: VocabularyService,
        main_window: MainWindow,
    ):
        super().__init__()

        self.canvas = canvas
        self.dictionary_service = dictionary_service
        self.vocabulary_service = vocabulary_service
        self.main_window = main_window

        # Transient state for word click context
        self.last_clicked_lemma: Optional[str] = None
        self.last_clicked_page_index: Optional[int] = None
        self.last_clicked_block_text: Optional[str] = None

        # Current session context (provided by ReaderController)
        self._current_volume: Optional[MangaVolume] = None
        self._current_page: int = 0

    def set_volume_context(self, volume: Optional[MangaVolume], current_page: int):
        """
        Update the current volume context (called by ReaderController).

        Args:
            volume: The currently loaded volume
            current_page: The current page number
        """
        self._current_volume = volume
        self._current_page = current_page

    @Slot(str, str, int, int, int, int)
    def handle_word_clicked(
        self,
        lemma: str,
        surface: str,
        mouse_x: int,
        mouse_y: int,
        page_index: int = -1,
        block_id: int = -1,
    ):
        """Handle word clicks from the canvas and show dictionary popup."""
        if self.dictionary_service is None:
            return

        # Store click context
        self.last_clicked_lemma = lemma
        self.last_clicked_page_index = page_index if page_index >= 0 else self._current_page
        self.last_clicked_block_text = None

        # Find the OCR block for sentence context
        if (
            self._current_volume is not None
            and self.last_clicked_page_index is not None
            and 0 <= self.last_clicked_page_index < self._current_volume.total_pages
        ):
            current_page = self._current_volume.get_page(self.last_clicked_page_index)
            clicked_block = None
            if block_id is not None and block_id >= 0 and block_id < len(current_page.ocr_blocks):
                clicked_block = current_page.ocr_blocks[block_id]
            else:
                clicked_block = current_page.find_block_at_position(mouse_x, mouse_y)
            if clicked_block is not None:
                self.last_clicked_block_text = clicked_block.full_text

        entry = self.dictionary_service.lookup(lemma, surface)

        # Check if word is already tracked
        is_tracked = self.vocabulary_service.is_word_tracked(lemma)

        payload = {
            # Normalize display to lemma so popup header shows base form (not conjugated surface)
            "surface": lemma or surface,
            # Preserve original clicked surface for future UI use if needed
            "surfaceOriginal": surface,
            "reading": entry.reading if entry else "",
            "partOfSpeech": entry.senses[0].pos[0] if entry and entry.senses and entry.senses[0].pos else "Unknown",
            "senses": [
                {"glosses": sense.glosses, "pos": sense.pos}
                for sense in entry.senses
            ]
            if entry
            else [],
            "mouseX": mouse_x,
            "mouseY": mouse_y,
            "notFound": entry is None,
            "isTracked": is_tracked,
            "lemma": lemma,
        }

        self.canvas.show_dictionary_popup(payload)

    @Slot(str, str, str)
    def handle_track_word(self, lemma: str, reading: str, part_of_speech: str):
        """Handle tracking a word from the dictionary popup."""
        if self._current_volume is None:
            raise RuntimeError("No volume loaded for tracking word")
        if self.last_clicked_block_text is None:
            raise RuntimeError("No block context available for tracking word")

        # Use the stored page from when the word was clicked, not current page
        page_index = (
            self.last_clicked_page_index
            if self.last_clicked_page_index is not None
            else self._current_page
        )
        if not (0 <= page_index < self._current_volume.total_pages):
            return

        sentence = self.last_clicked_block_text

        # Placeholder crop coordinates until block-based cropping is implemented
        crop_coords = {"x": 0, "y": 0, "width": 100, "height": 50}

        try:
            self.vocabulary_service.track_word(
                lemma=lemma,
                reading=reading,
                part_of_speech=part_of_speech,
                volume_path=self._current_volume.volume_path,
                page_index=page_index,
                crop_coordinates=crop_coords,
                sentence_text=sentence,
            )

            # Update UI to show tracked status (mark word with black border)
            self.canvas.add_tracked_lemma(lemma)

            self.main_window.show_info(
                "Word Tracked",
                f"Added '{lemma}' to your vocabulary!\nReading: {reading}\nType: {part_of_speech}",
            )
        except Exception as e:
            self.main_window.show_error(
                "Tracking Failed",
                f"Could not track word: {e}",
            )
