"""Main entry point for the manga reader application."""

import sys
from PySide6.QtWidgets import QApplication

from manga_reader.io import VolumeIngestor
from manga_reader.ui import MainWindow, MangaCanvas
from manga_reader.coordinators import ReaderController


def main():
    """
    Bootstrap the application following the Composition Root pattern.
    This is the only place that knows how to instantiate and wire all components.
    """
    # 1. Initialize Application
    app = QApplication(sys.argv)
    app.setApplicationName("Manga Reader")
    app.setOrganizationName("MangaReader")
    
    # 2. Initialize Infrastructure
    ingestor = VolumeIngestor()
    
    # 3. Construct UI
    canvas = MangaCanvas()
    main_window = MainWindow()
    main_window.set_canvas(canvas)
    
    # 4. Instantiate Coordinator (Dependency Injection)
    controller = ReaderController(
        main_window=main_window,
        canvas=canvas,
        ingestor=ingestor
    )
    
    # 5. Signal Wiring (Connect UI signals to Controller slots)
    main_window.volume_opened.connect(controller.handle_volume_opened)
    
    # 6. Show UI and start event loop
    main_window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
