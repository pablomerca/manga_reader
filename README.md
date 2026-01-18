# Manga Reader

A feature-rich Linux desktop manga reader and interactive vocabulary companion for Japanese learners. It renders Mokuro OCR overlays with word-level metadata, provides inline dictionary definitions, tracks vocabulary with contextual recall, and manages a persistent library of volumes.

## ✨ Key Features

### 📚 Volume Library Management
- **Persistent library** of manga volumes with SQLite-backed storage
- **Quick access** to previously read volumes with thumbnail previews

- **Volume metadata** tracking: title (editable), path, last opened date, page count
- **Smart recovery**: Automatic path relocation if a volume has been moved on disk
- **Ordered by recency**: Volumes sorted by last-opened timestamp for quick access

### 📖 Advanced Reading Experience
- **Mokuro OCR support**: Full-featured rendering of Mokuro JSON overlays with word-level metadata (lemma, surface form, reading)
- **Flexible page layout**: Single-page and dual-page (spread) viewing modes with zoom and pan controls
- **RTL navigation**: Arrow keys with right-to-left semantics (← = next page, → = previous page)
- **Zoom & Pan**: Mouse wheel zoom (0.2x to 5.0x), smooth panning for detailed manga reading
- **Noun highlighting** (Beta): Visual highlighting of extracted nouns for grammatical awareness

### 🔤 Dictionary & Vocabulary
- **Interactive dictionary**: Click any word to see inline definitions (Jamdict-backed)
- **Vocabulary tracking**: Track words with automatic lemma extraction via morphological analysis
- **Context viewing**: Right-side panel showing all appearances of tracked words across the current volume
- **Smart navigation**: Jump to any tracked word appearance with automatic page navigation and visual highlighting
- **Full-text context**: View surrounding text for each word appearance to aid recall
- **Persistence**: All tracked vocabulary saved to SQLite with appearance metadata (page, block coordinates)

### 🎯 Morphological Analysis
- **Automatic lemmatization**: Conjugated verbs, adjectives, and i-adjectives automatically reduced to dictionary form
- **Word type extraction**: Support for nouns, verbs (auxiliary verbs included), adjectives (i-adjectives, na-adjectives), and adverbs
- **Accurate POS tagging**: Via Janome morphological analyzer for reliable part-of-speech identification

### 📱 User Interface
- **Clean, modern design**: PySide6-based Qt desktop application
- **Responsive layout**: Main window with integrated manga canvas, dictionary popup, and context panel
- **Keyboard shortcuts**:
  - `Ctrl+O` — Open volume
  - `Ctrl+L` — Open library
  - `Ctrl+T` — Toggle view mode (single/double page)
  - `←/→` — Navigate pages (RTL aware)
  - `Escape` — Close dialogs/panels

## Quick Start

### Installation

1. Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install in editable mode:
```bash
pip install -e .
```

3. Run the application:
```bash
manga-reader              # After package installation
# or
python -m manga_reader.main
# or
python src/manga_reader/main.py
```

### Basic Usage

1. **Launch the app** — You'll see either the Library screen (if volumes are saved) or the Reader screen
2. **Open a volume** — File → Open Volume (Ctrl+O) and select a folder containing:
   - A `.mokuro` JSON file (Mokuro OCR output)
   - Matching page images (JPEG format)
3. **Read manga** — Navigate with arrow keys; zoom with mouse wheel
4. **Look up words** — Click any word to see its dictionary definition in a popup
5. **Track vocabulary** — Click "Track Word" in the popup to add it to your vocabulary list
6. **View context** — Right-click a tracked word in the context panel, or use "View Context" to see all appearances in the volume
7. **Manage library** — Ctrl+L to view your saved volumes; click to open any previous volume

## Architecture

The application follows a **strict layered architecture** with clear separation of concerns:

### Layer Structure

```
UI Layer (ui/)
    ↓ Signals/Slots (Qt)
Coordinators (coordinators/)
    ↓ Method Calls
Services (services/) + Domain (core/)
    ↓ 
Data Access (io/) + SQLite
```

### Key Modules

#### `core/` — Domain Entities
Pure Python data structures with no external dependencies:
- `MangaVolume` — Container for pages with metadata and access patterns
- `MangaPage` — Page dimensions, image path, and OCR blocks
- `OCRBlock` — Text area with bounding box (x, y, width, height) and word-level metadata
- `VocabularyWord` — Tracked word with lemma, readings, and appearance records

#### `io/` — Data Access
- `VolumeIngestor` — Parses Mokuro JSON files and constructs domain objects
- `DatabaseManager` — SQLite schema management (volumes, tracked words, word appearances)
- `LibraryRepository` — CRUD operations for volume library persistence

#### `services/` — Business Logic
- `MorphologyService` — Lemmatization, POS tagging, word extraction (nouns, verbs, adjectives, adverbs)
- `DictionaryService` — Word lookups via Jamdict with caching
- `VocabularyService` — Tracked word management, appearance recording, lemma-based deduplication
- `ThumbnailService` — Volume thumbnail generation and caching

#### `ui/` — User Interface
- `MainWindow` — Application window, menu bar, file dialogs, screen switching
- `LibraryScreen` — Grid view of volumes with titles, thumbnails, editing, deletion
- `MangaCanvas` — QWebEngineView-based renderer for Mokuro overlays with zoom/pan via JavaScript
- `WordContextPanel` — Right-side panel listing tracked word appearances with navigation
- `WordContextPopup` — Inline definition popup triggered by word click
- Plus web assets: `viewer.html`, `viewer.js` (with modular JS controllers), `styles.css`

#### `coordinators/` — Orchestration
Specialized coordinators following the Single Responsibility Principle:
- `ReaderController` — Session state (current volume, page, view mode) and page navigation
- `WordInteractionCoordinator` — Word clicks, dictionary popup display, vocabulary tracking
- `ContextPanelCoordinator` — Context panel lifecycle, appearance navigation, highlighting
- `ContextSyncCoordinator` — Synchronizing vocabulary across page changes
- `LibraryCoordinator` — Library management (add, open, delete, relocation)

#### `main.py` — Composition Root
The **only file** that knows how to instantiate all components. Handles:
- Service initialization
- UI construction
- Dependency injection into coordinators
- Signal/slot wiring

## Project Structure

```
src/manga_reader/
├── core/                          # Domain entities (no UI deps)
│   ├── manga_volume.py
│   ├── manga_page.py
│   └── ocr_block.py
├── io/                            # Data access & persistence
│   ├── volume_ingestor.py
│   ├── database_manager.py
│   └── library_repository.py
├── services/                      # Application services
│   ├── morphology_service.py
│   ├── dictionary_service.py
│   ├── vocabulary_service.py
│   └── thumbnail_service.py
├── ui/                            # PySide6 UI & web assets
│   ├── main_window.py
│   ├── library_screen.py
│   ├── manga_canvas.py
│   ├── word_context_panel.py
│   ├── word_context_popup.py
│   └── assets/
│       ├── viewer.js              # Main viewer controller (modular design)
│       ├── viewer.html
│       ├── styles.css
│       └── modules/               # JS controller modules
│           ├── ZoomController.js
│           ├── PanController.js
│           ├── LayoutManager.js
│           ├── PageRenderer.js
│           ├── PopupManager.js
│           ├── OverlayManager.js  # Highlight & visual overlays
│           ├── EventRouter.js
│           └── TextFormatter.js
├── coordinators/                  # Specialized orchestrators
│   ├── reader_controller.py
│   ├── library_coordinator.py
│   ├── word_interaction_coordinator.py
│   ├── context_panel_coordinator.py
│   └── context_sync_coordinator.py
└── main.py                        # Entry point & Composition Root

tests/                             # Comprehensive test suite
├── coordinators/                  # 30+ tests for coordinators
├── services/                      # 40+ tests for services
├── ui/                            # 15+ tests for UI logic
├── io/                            # 20+ tests for data access
└── integration/                   # 5 end-to-end workflow tests

```

## Test Coverage

**166 Tests** covering:
- ✅ Coordinators (30+ tests) — Navigation, word tracking, context panel lifecycle
- ✅ Services (40+ tests) — Morphology, dictionary, vocabulary tracking
- ✅ UI Components (15+ tests) — Canvas rendering, data preparation
- ✅ Data Access (20+ tests) — Database schema, CRUD operations, library persistence
- ✅ Integration (5 tests) — Full user workflows (add → open → delete, title editing, relocation, persistence)

Run tests with:
```bash
pytest                            # Run all tests
pytest -v                         # Verbose output
pytest tests/integration/         # Integration tests only
pytest -k "vocabulary"            # Run specific test
```

## System Requirements

- **OS**: Linux (tested on Ubuntu 20.04, Pop!_OS, Fedora)
- **Python**: 3.10 or later
- **Dependencies**:
  - PySide6 (Qt6 bindings for Python)
  - Janome (morphological analyzer)
  - Jamdict (Japanese dictionary)
  - Pillow (image processing)

## Sample Data

The repository includes test fixtures:
- `testVol/` — Sample Mokuro volume with test pages
- `testVol2/` — Additional test volume for multi-volume testing

## Known Limitations & Future Work

### Current Limitations
- Database stored in project root (should be moved to `~/.local/share/manga-reader/` in production)
- Noun highlighting is experimental (Beta status)
- No Anki export yet
- No search functionality for tracked words

### Planned Features
- **Vocabulary Manager Modal** — Full-featured vocabulary list with search and filtering
- **Smart Anki/TSV Export** — Export tracked words with context and readings
- **Block-level Sentence Extraction** — Better capture of full sentences when tracking from canvas
- **Reading Progress** — Bookmark pages, reading session tracking
- **Custom Dictionaries** — Support for user-defined dictionary entries

## License

TBD

## Contributing

Contributions welcome! Please ensure:
1. All tests pass: `pytest`
2. Code follows SOLID principles
3. Layered architecture is respected
4. Dependency injection is used (no globals)
5. New features include tests

## Credits

Built by a Japanese learner for Japanese learners. Powered by:
- **Mokuro** — Open-source OCR processing for manga
- **Jamdict** — Japanese-English dictionary
- **Dango** — Morphological analyzer
- **Qt/PySide6** — Cross-platform desktop UI

