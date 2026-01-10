# Manga Reader

A Linux desktop manga reader and vocabulary companion for Japanese learners. It renders Mokuro OCR overlays, surfaces dictionary definitions, and tracks vocabulary with contextual recall.

## Quick Start

1) Create and activate a virtualenv
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2) Install in editable mode
```bash
pip install -e .
```

3) Run the app
```bash
manga-reader           # after install
# or
python -m manga_reader.main
# or
python src/manga_reader/main.py
```

## How to Use

1) Launch the app
2) File → Open Volume (Ctrl+O) and choose a folder containing:
   - A `.mokuro` JSON file (Mokuro OCR output)
   - The matching page images (JPEG)
3) Read with overlays. Click a word to open the dictionary popup.
4) Track a word from the popup, then click **View Context** to see all occurrences in the right-side panel.
5) Navigate pages with the left/right arrow keys (RTL semantics: Left = next, Right = previous) and switch single/double page view from the View menu.

## Current Features

- Volume loading: validate Mokuro JSON, resolve page images, load full volume
- Page rendering: OCR overlays with word-level metadata (lemma/surface) and noun highlighting
- Navigation: single/double page modes with RTL keyboard navigation (arrow keys)
- Dictionary popup: inline definitions on word click (Jamdict-backed stub)
- Vocabulary tracking: SQLite-backed tracking with idempotent upserts and morphology-based lemma/reading
- Context panel: split-view panel listing all appearances of a tracked word; click to jump to that page
- Clean architecture: specialized coordinators handle navigation, word interactions, and context panel lifecycle independently

## Architecture (Layered)

- `core/` — Domain entities (`MangaVolume`, `MangaPage`, `OCRBlock`, vocabulary entities). Pure Python, no UI imports.
- `io/` — Data access (`VolumeIngestor`, `DatabaseManager`). Parses Mokuro JSON, manages SQLite schema & CRUD.
- `services/` — Application services (`MorphologyService`, `DictionaryService`, `VocabularyService`).
- `ui/` — Widgets (`MainWindow`, `MangaCanvas`, `WordContextPanel`) plus web assets (`viewer.html/js/css`).
- `coordinators/` — Specialized coordinators following single responsibility principle:
  - `ReaderController` — Session management and page navigation
  - `WordInteractionCoordinator` — Word clicks, dictionary popup, vocabulary tracking
  - `ContextPanelCoordinator` — Context panel lifecycle and appearance navigation
- `main.py` — Composition root: builds all components, wires dependencies, connects signals.

## Project Structure

```
src/manga_reader/
├── core/              # Domain entities (no UI deps)
├── io/                # Volume ingestor, SQLite database manager
├── services/          # Morphology, dictionary, vocabulary services
├── ui/                # PySide6 widgets and web assets (QWebEngineView)
├── coordinators/      # Specialized coordinators (navigation, word interaction, context panel)
└── main.py            # Composition root / entry point
tests/                 # Pytest suite (mirrors src/) - 93 tests
docs/                  # Architecture notes and specs
```

## Development

- Run tests: `pytest`
- Lint/format (if configured): `ruff check src/ tests/`, `black src/ tests/`
- Sample data: `testVol/`, `testVol2/` contain Mokuro fixtures

## Requirements

- Python 3.10+
- PySide6
- Linux desktop (tested on Ubuntu/Pop!_OS)
- Mokuro-processed manga volumes (JSON + JPEGs)

## Roadmap / Upcoming

- Vocabulary manager modal (list + search tracked words)
- UX polish for dictionary popup (spacing, accessibility)
- Better capture of block coordinates/sentences when tracking from canvas selection
- Double-page rendering polish and zoom/pan refinements
- Optional Anki / TSV export of tracked vocabulary

## License

TBD
