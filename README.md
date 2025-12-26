# Manga Reader

A Linux desktop vocabulary companion for intermediate Japanese learners.

## Installation

1. Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install the package in editable mode with dependencies:
```bash
pip install -e .
```

## Running the Application

### From the command line (after installation):
```bash
manga-reader
```

### Or directly with Python:
```bash
python -m manga_reader.main
```

### Or from the repository root:
```bash
python src/manga_reader/main.py
```

## Usage

1. Launch the application
2. Click **File → Open Volume** (or press `Ctrl+O`)
3. Select a folder containing:
   - A `.mokuro` file (Mokuro OCR JSON output)
   - Corresponding JPEG images of manga pages

The application will load the volume and display the first page with text overlays.

## Current Features (MVP - Iteration 1)

- ✅ Open and load Mokuro-processed manga volumes
- ✅ Display manga pages with OCR text overlays
- ✅ Parse and validate Mokuro JSON structure
- ✅ Basic page navigation state management

## Coming Soon

- Page navigation (next/previous, keyboard shortcuts)
- Dictionary lookups on text click
- Vocabulary tracking
- Contextual recall (jump to prior appearances)
- Anki export

## Project Structure

```
manga_reader/
├── src/
│   └── manga_reader/
│       ├── core/           # Domain entities (MangaVolume, MangaPage, OCRBlock)
│       ├── io/             # Data access (VolumeIngestor)
│       ├── ui/             # PySide6 UI components (MainWindow, MangaCanvas)
│       ├── coordinators/   # Application logic (ReaderController)
│       └── main.py         # Application entry point
└── tests/                  # Test suite
```

## Requirements

- Python 3.9+
- PySide6 (Qt for Python)
- Linux (Ubuntu/Pop!_OS recommended)
- Mokuro-processed manga volumes

## License

TBD
