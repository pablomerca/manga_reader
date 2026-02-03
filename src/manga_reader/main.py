"""Main entry point for the manga reader application."""

import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from manga_reader.coordinators import (
    LibraryCoordinator,
    ReaderController,
    WordInteractionCoordinator,
    ContextPanelCoordinator,
    ContextSyncCoordinator,
    SentenceAnalysisCoordinator,
    DictionaryPanelCoordinator,
)
from manga_reader.io import DatabaseManager, LibraryRepository, VolumeIngestor
from manga_reader.services import (
    DictionaryService,
    MorphologyService,
    ThumbnailService,
    VocabularyService,
    FileTranslationCache,
    GeminiTranslationService,
    GeminiExplanationService,
    SettingsManager,
)
from manga_reader.ui import LibraryScreen, MainWindow, MangaCanvas, WordContextPanel, SentenceAnalysisPanel, DictionaryPanel


def configure_qt_rendering() -> None:
    """
    Configure Qt rendering backend for stability.

    Environment override:
      - MANGA_READER_FORCE_SOFTWARE_RENDERING=1 -> force software rendering
      - MANGA_READER_FORCE_SOFTWARE_RENDERING=0 -> force default (GPU)

    If unset, software rendering is enabled by default on Linux.
    """
    setting = os.environ.get("MANGA_READER_FORCE_SOFTWARE_RENDERING")
    if setting is not None:
        force_software = setting.lower() in {"1", "true", "yes"}
    else:
        force_software = sys.platform.startswith("linux")

    if not force_software:
        return

    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")


def main():
    """
    Bootstrap the application following the Composition Root pattern.
    This is the only place that knows how to instantiate and wire all components.
    """

    # Work around GPU/GL context creation failures (optional)
    configure_qt_rendering()

    # 1. Initialize Application
    app = QApplication(sys.argv)
    print("DEBUG: QApplication initialized successfully.")
    app.setApplicationName("Manga Reader")
    app.setOrganizationName("MangaReader")
    
    # 2. Initialize Services & Infrastructure
    print("DEBUG: Initializing services and infrastructure...")
    morphology_service = MorphologyService()
    dictionary_service = DictionaryService()
    ingestor = VolumeIngestor()
    settings_manager = SettingsManager()
    translation_cache = FileTranslationCache()
    translation_service = GeminiTranslationService()
    explanation_service = GeminiExplanationService()
    print("DEBUG: Services initialized.")

    # TODO: In production, migrate to proper OS-specific paths (~/.local/share, etc.)

    # For MVP, store database in project root for fast dev iteration
    project_root = Path(__file__).parent.parent.parent

    db_path = project_root / "vocab.db"
    print(f"DEBUG: Database path: {db_path}")
    database_manager = DatabaseManager(db_path)
    database_manager.ensure_schema()
    vocabulary_service = VocabularyService(database_manager, morphology_service)
    print("DEBUG: Database manager initialized.")
    
    # Initialize library persistence and thumbnail service
    library_repository = LibraryRepository(database_manager.connection)
    thumbnail_service = ThumbnailService()
    
    # 3. Construct UI (injecting dependencies)
    print("DEBUG: Building UI components...")
    library_screen = LibraryScreen()
    print("DEBUG: LibraryScreen created.")
    canvas = MangaCanvas(morphology_service=morphology_service)
    print("DEBUG: MangaCanvas created.")
    context_panel = WordContextPanel()
    sentence_panel = SentenceAnalysisPanel()
    dictionary_panel = DictionaryPanel()
    main_window = MainWindow()
    print("DEBUG: MainWindow created.")
    main_window.set_canvas(canvas)
    main_window.set_context_panel(context_panel)
    main_window.set_sentence_panel(sentence_panel)
    main_window.set_dictionary_panel(dictionary_panel)
    print("DEBUG: Canvas and panels attached to MainWindow.")
    
    # 4. Instantiate Coordinators (Dependency Injection)
    print("DEBUG: Instantiating coordinators...")
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

    sentence_analysis_coordinator = SentenceAnalysisCoordinator(
        main_window=main_window,
        translation_service=translation_service,
        translation_cache=translation_cache,
        explanation_service=explanation_service,
        settings_manager=settings_manager,
    )

    dictionary_panel_coordinator = DictionaryPanelCoordinator(
        panel=dictionary_panel,
        dictionary_service=dictionary_service,
        main_window=main_window,
    )
    
    # Create library coordinator (pass to reader controller)
    library_coordinator = LibraryCoordinator(
        library_screen=library_screen,
        library_repository=library_repository,
        volume_ingestor=ingestor,
        thumbnail_service=thumbnail_service,
        main_window=main_window,
    )
    print("DEBUG: Coordinators initialized.")

    controller = ReaderController(
        main_window=main_window,
        canvas=canvas,
        ingestor=ingestor,
        word_interaction=word_interaction,
        context_coordinator=context_coordinator,
        context_sync_coordinator=context_sync_coordinator,
        vocabulary_service=vocabulary_service,
        library_coordinator=library_coordinator,
        sentence_analysis_coordinator=sentence_analysis_coordinator,
        sentence_analysis_panel=sentence_panel,
        dictionary_panel_coordinator=dictionary_panel_coordinator,
    )
    print("DEBUG: ReaderController initialized.")
    
    # 5. Inject controller into MainWindow and let it wire signals internally
    main_window.set_controller(controller)
    # Route word interactions to dedicated coordinator
    canvas.word_clicked.connect(word_interaction.handle_word_clicked)
    canvas.track_word_requested.connect(word_interaction.handle_track_word)
    canvas.view_word_context_requested.connect(controller.handle_view_word_context)
    # Route lemma-based context requests via context coordinator
    canvas.view_context_by_lemma_requested.connect(context_coordinator.handle_view_context_by_lemma)
    # Route dictionary panel requests via dictionary panel coordinator
    if dictionary_panel_coordinator:
        canvas.show_full_definition_requested.connect(dictionary_panel_coordinator.handle_show_full_definition)
    
    # Route context panel appearance navigation with highlighting
    context_panel.appearance_clicked_with_coords.connect(
        controller.handle_navigate_to_appearance
    )
    print("DEBUG: Signal connections established.")

    # Persist reading progress when the application is closing
    app.aboutToQuit.connect(controller.handle_app_closing)

    # Connect coordinator requests back to controller (already wired inside controller ctor)
    
    # 6. Show library on startup
    print("DEBUG: Displaying library view...")
    library_coordinator.show_library()
    print("DEBUG: Library view displayed.")
    
    # 7. Start event loop
    print("DEBUG: Showing main window and starting event loop...")
    main_window.show()
    print("DEBUG: Main window shown. Event loop starting.")
    
    return app.exec()


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code if exit_code is not None else 0)
    except Exception as e:
        print(f"FATAL EXCEPTION: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
