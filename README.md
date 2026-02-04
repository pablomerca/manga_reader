# Manga Reader

A desktop app for reading manga with OCR overlays, inline dictionary lookups, and vocabulary tracking—built for Japanese learners.

##  Key Features

###  Reading Experience
- Open Mokuro volumes (.mokuro + images) with single or double-page layouts
- Toggle between single-page and double-page (spread) modes with smart portrait/landscape detection
- Zoom and pan with the mouse wheel; right-to-left page navigation
- Lazy text rendering for smooth performance—hover over blocks to reveal OCR text

###  Library Management
- Persistent volume library with thumbnails and automatic sorting by recent use
- Edit volume titles and relocate moved volumes
- Quick access to all your manga in one place
- Automatic thumbnail generation and caching from first page
- Smart volume ordering by most recently accessed

###  Dictionary & Vocabulary
- Click words for instant dictionary definitions (powered by Jamdict)
- Track words to your personal vocabulary list with automatic lemmatization
- View all appearances of tracked words across the volume with context
- Kanji Navigation: Click kanji characters in dictionary entries to navigate through kanji definitions with breadcrumb trail
- Click on word appearances to jump to exact location with visual highlight overlay
- Smart verb tracking: conjugated forms (食べた, 食べている) automatically link to base form (食べる)
- Support for nouns, verbs, auxiliary verbs, adjectives (i-adjectives, na-adjectives), and adverbs

###  AI-Powered Sentence Analysis
- Translate blocks with Google Gemini AI
- Get detailed explanations of grammar, idioms, and cultural context
- Results are cached per-volume for instant re-access
- Separate panel for sentence analysis with copy/translate/explain actions

## Quick Start
1. **Prereqs:** Linux, Python 3.10+, Mokuro output (JSON + matching images)
2. **Install:**
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -e .
   ```
3. **Run:** `manga-reader` (or `python -m manga_reader.main`)
4. **Open a volume:** File → Open (Ctrl+O) and choose the folder with the `.mokuro` file and images

## Basic Usage
- Navigate pages with ←/→ ; zoom with the mouse wheel; pan by dragging
- Hover over text blocks to reveal OCR text overlay on manga dialog
- Click any word to open the pop up dictionary, which can be expanded to a side panel with full definitions
- Click kanji characters in definitions to navigate through kanji entries (breadcrumb navigation)
- Use "Track Word" to save words to your vocabulary list
- Right-click blocks to open the sentence analysis panel for translation and explanation
- Click word appearances in context panel to jump to exact page with highlighted block
- Ctrl+L opens your library; pick a volume to resume reading
- Ctrl+V shows your vocabulary list (simple view)
- Ctrl+T toggles between single-page and double-page spread modes

## Controls 
- **Ctrl+O**: Open volume
- **Ctrl+L**: Library view with thumbnail grid
- **Ctrl+V**: Vocabulary list (simple view)
- **Ctrl+T**: Toggle single/double page display mode
- **Ctrl+Shift+S**: Sync context (refresh tracked word appearances)
- **← / →**: Page navigation (right-to-left reading order)
- **Mouse wheel**: Zoom in/out
- **Click + drag**: Pan while zoomed
- **Click word**: Open dictionary side panel
- **Click kanji**: Navigate to kanji entry (in dictionary panel)
- **Escape**: Close dialogs/panels

## System Requirements
- Linux (tested on Ubuntu/PopOS)
- Python 3.10+
- Mokuro output: one `.mokuro` JSON plus matching page images (JPEG)
- Google Gemini API key (optional, for translation/explanation features)

## Data & Samples
- Library and vocabulary are stored locally in SQLite (current default: project folder)
- Sample Mokuro data: `testVol/` and `testVol2/`

## Current Status
- ✅ **Core reading features complete**: Single/double-page layouts, zoom/pan, lazy text rendering, RTL navigation
- ✅ **Library management complete**: Persistent SQLite storage, thumbnail grid, volume relocation, title editing
- ✅ **Dictionary system complete**: Full word lookups with Jamdict, kanji navigation with breadcrumbs, furigana display
- ✅ **Vocabulary tracking complete**: Smart lemmatization, word appearances with context, block highlighting for navigation
- ✅ **AI-powered analysis complete**: Google Gemini (gemini-2.0-flash) translation & explanation with caching
- ✅ **Comprehensive test suite**: 166+ tests across all architectural layers
- 🚧 **In progress**: Full vocabulary manager UI, Anki export functionality

## License
TBD
