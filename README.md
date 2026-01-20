# Manga Reader

A Linux desktop app for reading manga with Mokuro OCR overlays, inline dictionary lookups, and vocabulary tracking—built for Japanese learners.

## ✨ Key Features

### 📖 Reading Experience
- Open Mokuro volumes (.mokuro + images) with single or double-page layouts
- Zoom and pan with the mouse wheel; right-to-left page navigation
- Lazy text rendering for smooth performance

### 📚 Library Management
- Persistent volume library with thumbnails and automatic sorting by recent use
- Edit volume titles and relocate moved volumes
- Quick access to all your manga in one place

### 🔤 Dictionary & Vocabulary
- Click words for instant dictionary definitions (powered by Jamdict)
- Track words to your personal vocabulary list with automatic lemmatization
- View all appearances of tracked words across the volume with context
- Jump to any word appearance with automatic page navigation and highlighting
- Smart verb tracking: conjugated forms (食べた, 食べている) automatically link to base form (食べる)
- Support for nouns, verbs, auxiliary verbs, adjectives (i-adjectives, na-adjectives), and adverbs

### 🤖 AI-Powered Sentence Analysis
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
- Navigate pages with ←/→ (RTL semantics); zoom with the mouse wheel
- Click any word to see its definition; use "Track Word" to save it
- Right-click blocks to open the sentence analysis panel for translation and explanation
- Use the context panel (right side) to jump to any appearance of a tracked word
- Ctrl+L opens your library; pick a volume to resume reading
- Ctrl+V shows your vocabulary list (simple view)

## Controls at a Glance
- Ctrl+O: Open volume
- Ctrl+L: Library view
- Ctrl+V: Vocabulary list (simple view)
- Ctrl+Shift+S: Sync context (refresh tracked word appearances)
- Ctrl+T: Toggle single/double page
- ← / →: Page navigation (RTL)
- Right-click block: Open sentence analysis panel
- Escape: Close dialogs/panels

## System Requirements
- Linux (tested on Ubuntu/Pop!/Fedora)
- Python 3.10+
- Mokuro output: one `.mokuro` JSON plus matching page images (JPEG)
- Google Gemini API key (optional, for translation/explanation features)

## Data & Samples
- Library and vocabulary are stored locally in SQLite (current default: project folder)
- Sample Mokuro data: `testVol/` and `testVol2/`

## Current Status
- Core features complete: reading, library, vocabulary tracking, dictionary lookups
- AI translation/explanation powered by Google Gemini (requires API key)
- Smart morphological analysis with automatic verb conjugation handling
- Comprehensive test suite with 166+ tests across all layers
- Experimental noun highlighting; full vocabulary manager and Anki export coming soon

## License
TBD
