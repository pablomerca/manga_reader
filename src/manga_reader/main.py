"""Main entry point for the manga reader application."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from manga_reader.coordinators import ReaderController, WordInteractionCoordinator
from manga_reader.io import DatabaseManager, VolumeIngestor
from manga_reader.services import DictionaryService, MorphologyService, VocabularyService
from manga_reader.ui import MainWindow, MangaCanvas, WordContextPanel


def main():
    """
    Bootstrap the application following the Composition Root pattern.
    This is the only place that knows how to instantiate and wire all components.
    """
    # 1. Initialize Application
    app = QApplication(sys.argv)
    app.setApplicationName("Manga Reader")
    app.setOrganizationName("MangaReader")
    
    # 2. Initialize Services & Infrastructure
    morphology_service = MorphologyService()
    dictionary_service = DictionaryService()
    ingestor = VolumeIngestor()

    # TODO: In production, migrate to proper OS-specific paths (~/.local/share, etc.)

    # For MVP, store database in project root for fast dev iteration
    project_root = Path(__file__).parent.parent.parent

    db_path = project_root / "vocab.db"
    database_manager = DatabaseManager(db_path)
    database_manager.ensure_schema()
    vocabulary_service = VocabularyService(database_manager, morphology_service)
    
    # 3. Construct UI (injecting dependencies)
    canvas = MangaCanvas(morphology_service=morphology_service)
    context_panel = WordContextPanel()
    main_window = MainWindow()
    main_window.set_canvas(canvas)
    main_window.set_context_panel(context_panel)
    
    # 4. Instantiate Coordinators (Dependency Injection)
    word_interaction = WordInteractionCoordinator(
        canvas=canvas,
        dictionary_service=dictionary_service,
        vocabulary_service=vocabulary_service,
        main_window=main_window,
    )

    controller = ReaderController(
        main_window=main_window,
        canvas=canvas,
        ingestor=ingestor,
        dictionary_service=dictionary_service,
        vocabulary_service=vocabulary_service,
        context_panel=context_panel,
        word_interaction=word_interaction,
    )
    
    # 5. Inject controller into MainWindow and let it wire signals internally
    main_window.set_controller(controller)
    # Route word interactions to dedicated coordinator
    canvas.word_clicked.connect(word_interaction.handle_word_clicked)
    canvas.track_word_requested.connect(word_interaction.handle_track_word)
    canvas.view_word_context_requested.connect(controller.handle_view_word_context)
    canvas.view_context_by_lemma_requested.connect(controller.handle_view_context_by_lemma)
    
    # 6. Show UI and start event loop
    main_window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
