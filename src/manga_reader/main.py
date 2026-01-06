"""Main entry point for the manga reader application."""

import sys

from PySide6.QtWidgets import QApplication

from manga_reader.coordinators import ReaderController
from manga_reader.io import VolumeIngestor
from manga_reader.services import DictionaryService, MorphologyService
from manga_reader.ui import MainWindow, MangaCanvas


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
    
    # 3. Construct UI (injecting dependencies)
    canvas = MangaCanvas(morphology_service=morphology_service)
    main_window = MainWindow()
    main_window.set_canvas(canvas)
    
    # 4. Instantiate Coordinator (Dependency Injection)
    controller = ReaderController(
        main_window=main_window,
        canvas=canvas,
        ingestor=ingestor,
        dictionary_service=dictionary_service,
    )
    
    # 5. Inject controller into MainWindow and let it wire signals internally
    main_window.set_controller(controller)
    canvas.word_clicked.connect(controller.handle_word_clicked)
    
    # 6. Show UI and start event loop
    main_window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
