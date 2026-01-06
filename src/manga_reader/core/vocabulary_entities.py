"""Vocabulary tracking entities used across services and persistence."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class TrackedWord:
    id: Optional[int]
    lemma: str
    reading: str
    part_of_speech: str
    date_added: Optional[str]


@dataclass
class MangaVolumeEntry:
    id: Optional[int]
    path: Path
    name: str


@dataclass
class WordAppearance:
    id: Optional[int]
    word_id: int
    volume_id: int
    page_index: int
    crop_coordinates: Dict[str, float]
    sentence_text: str
    volume_name: Optional[str] = None
    volume_path: Optional[Path] = None
