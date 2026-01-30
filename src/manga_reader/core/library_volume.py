"""Domain entity for library volume metadata."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LibraryVolume:
    """Represents a manga volume in the library collection.
    
    Attributes:
        id: Unique identifier in the database.
        title: Display title of the volume (customizable by user).
        folder_path: Absolute path to the directory containing .mokuro file.
        cover_image_path: Path to cached thumbnail image.
        date_added: Unix timestamp when volume was added to library.
        last_opened: Unix timestamp when volume was last opened.
        last_page_read: 0-indexed page number last read by the user.
    """

    id: int
    title: str
    folder_path: Path
    cover_image_path: Path
    date_added: int
    last_opened: int
    last_page_read: int
