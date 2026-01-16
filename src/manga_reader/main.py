"""Main entry point for the manga reader application."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from manga_reader.coordinators import (
    LibraryCoordinator,
    ReaderController,
    WordInteractionCoordinator,
    ContextPanelCoordinator,
    ContextSyncCoordinator,
)
from manga_reader.io import DatabaseManager, LibraryRepository, VolumeIngestor
from manga_reader.services import DictionaryService, MorphologyService, ThumbnailService, VocabularyService
from manga_reader.ui import LibraryScreen, MainWindow, MangaCanvas, WordContextPanel


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
    
    # Initialize library persistence and thumbnail service
    library_repository = LibraryRepository(database_manager.connection)
    thumbnail_service = ThumbnailService()
    
    # 3. Construct UI (injecting dependencies)
    library_screen = LibraryScreen()
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

    context_coordinator = ContextPanelCoordinator(
        context_panel=context_panel,
        vocabulary_service=vocabulary_service,
        main_window=main_window,
        word_interaction=word_interaction,
    )

    context_sync_coordinator = ContextSyncCoordinator(
        main_window=main_window,
        vocabulary_service=vocabulary_service,
        morphology_service=morphology_service,
    )
    
    # Create library coordinator (pass to reader controller)
    library_coordinator = LibraryCoordinator(
        library_screen=library_screen,
        library_repository=library_repository,
        volume_ingestor=ingestor,
        thumbnail_service=thumbnail_service,
        main_window=main_window,
    )

    controller = ReaderController(
        main_window=main_window,
        canvas=canvas,
        ingestor=ingestor,
        word_interaction=word_interaction,
        context_coordinator=context_coordinator,
        context_sync_coordinator=context_sync_coordinator,
        vocabulary_service=vocabulary_service,
        library_coordinator=library_coordinator,
    )
    
    # 5. Inject controller into MainWindow and let it wire signals internally
    main_window.set_controller(controller)
    # Route word interactions to dedicated coordinator
    canvas.word_clicked.connect(word_interaction.handle_word_clicked)
    canvas.track_word_requested.connect(word_interaction.handle_track_word)
    canvas.view_word_context_requested.connect(controller.handle_view_word_context)
    # Route lemma-based context requests via context coordinator
    canvas.view_context_by_lemma_requested.connect(context_coordinator.handle_view_context_by_lemma)

    # Connect coordinator requests back to controller (already wired inside controller ctor)
    
    # 6. Show library on startup
    library_coordinator.show_library()
    
    # 7. Start event loop
    main_window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
