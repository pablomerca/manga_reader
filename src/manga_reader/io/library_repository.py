"""Data access layer for library volume persistence."""

import sqlite3
import time
from pathlib import Path
from typing import List

from manga_reader.core import LibraryVolume


class LibraryRepository:
    """Manages persistence of library volumes in the database.
    
    This repository follows the failing-fast philosophy: all operations
    raise exceptions rather than returning None. A valid LibraryVolume
    object is always guaranteed on success.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Initialize repository with database connection.
        
        Args:
            connection: SQLite connection with row_factory set and schema created.
            
        Raises:
            RuntimeError: If connection is None or invalid.
        """
        if connection is None:
            raise RuntimeError("Database connection required")
        self.connection = connection
        self.connection.row_factory = sqlite3.Row

    def add_volume(
        self,
        title: str,
        folder_path: Path,
        cover_image_path: Path,
    ) -> LibraryVolume:
        """Add a new volume to the library or update existing.
        
        Uses folder_path as UNIQUE constraint to prevent duplicates.
        
        Args:
            title: Display title of the volume.
            folder_path: Absolute path to volume folder.
            cover_image_path: Path to cached thumbnail image.
            
        Returns:
            LibraryVolume: The created/updated volume entity.
            
        Raises:
            RuntimeError: If database write fails.
        """
        folder_path = Path(folder_path).resolve()
        cover_image_path = Path(cover_image_path).resolve()
        now = int(time.time())

        try:
            cur = self.connection.cursor()
            cur.execute(
                """
                INSERT INTO library_volumes (
                    title, folder_path, cover_image_path, date_added, last_opened
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(folder_path) DO UPDATE SET
                    title = excluded.title,
                    cover_image_path = excluded.cover_image_path,
                    last_opened = excluded.last_opened
                """,
                (title, str(folder_path), str(cover_image_path), now, now),
            )
            self.connection.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to add volume to library: {e}") from e

        return self.get_volume_by_path(folder_path)

    def get_volume_by_path(self, folder_path: Path) -> LibraryVolume:
        """Retrieve a volume by its folder path.
        
        Args:
            folder_path: Absolute path to volume folder.
            
        Returns:
            LibraryVolume: The volume entity.
            
        Raises:
            RuntimeError: If volume not found.
        """
        folder_path = Path(folder_path).resolve()
        try:
            cur = self.connection.cursor()
            cur.execute(
                """
                SELECT id, title, folder_path, cover_image_path, date_added, last_opened
                FROM library_volumes
                WHERE folder_path = ?
                """,
                (str(folder_path),),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError(
                    f"Volume not found in library: {folder_path}"
                )
            return self._row_to_library_volume(row)
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to retrieve volume: {e}") from e

    def get_all_volumes(self) -> List[LibraryVolume]:
        """Retrieve all volumes in the library.
        
        Volumes are ordered by last_opened descending (most recent first).
        
        Returns:
            List[LibraryVolume]: List of all volumes (empty if no volumes exist).
            
        Raises:
            RuntimeError: If database query fails.
        """
        try:
            cur = self.connection.cursor()
            cur.execute(
                """
                SELECT id, title, folder_path, cover_image_path, date_added, last_opened
                FROM library_volumes
                ORDER BY last_opened DESC
                """
            )
            rows = cur.fetchall()
            return [self._row_to_library_volume(row) for row in rows]
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to retrieve volumes: {e}") from e

    def update_title(self, folder_path: Path, new_title: str) -> LibraryVolume:
        """Update the title of a volume.
        
        Args:
            folder_path: Absolute path to volume folder.
            new_title: New display title (must not be empty).
            
        Returns:
            LibraryVolume: The updated volume entity.
            
        Raises:
            RuntimeError: If title is empty or database write fails.
        """
        if not new_title or not new_title.strip():
            raise RuntimeError("Volume title cannot be empty")

        folder_path = Path(folder_path).resolve()
        try:
            cur = self.connection.cursor()
            cur.execute(
                """
                UPDATE library_volumes
                SET title = ?
                WHERE folder_path = ?
                """,
                (new_title.strip(), str(folder_path)),
            )
            if cur.rowcount == 0:
                raise RuntimeError(f"Volume not found: {folder_path}")
            self.connection.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to update volume title: {e}") from e

        return self.get_volume_by_path(folder_path)

    def update_last_opened(self, folder_path: Path) -> LibraryVolume:
        """Update the last_opened timestamp for a volume.
        
        Args:
            folder_path: Absolute path to volume folder.
            
        Returns:
            LibraryVolume: The updated volume entity.
            
        Raises:
            RuntimeError: If volume not found or database write fails.
        """
        folder_path = Path(folder_path).resolve()
        now = int(time.time())

        try:
            cur = self.connection.cursor()
            cur.execute(
                """
                UPDATE library_volumes
                SET last_opened = ?
                WHERE folder_path = ?
                """,
                (now, str(folder_path)),
            )
            if cur.rowcount == 0:
                raise RuntimeError(f"Volume not found: {folder_path}")
            self.connection.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to update last_opened: {e}") from e

        return self.get_volume_by_path(folder_path)

    def delete_volume(self, folder_path: Path) -> None:
        """Remove a volume from the library (does NOT delete files).
        
        Args:
            folder_path: Absolute path to volume folder.
            
        Raises:
            RuntimeError: If volume not found or database write fails.
        """
        folder_path = Path(folder_path).resolve()

        try:
            cur = self.connection.cursor()
            cur.execute(
                """
                DELETE FROM library_volumes
                WHERE folder_path = ?
                """,
                (str(folder_path),),
            )
            if cur.rowcount == 0:
                raise RuntimeError(f"Volume not found: {folder_path}")
            self.connection.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to delete volume: {e}") from e

    @staticmethod
    def _row_to_library_volume(row: sqlite3.Row) -> LibraryVolume:
        """Convert database row to LibraryVolume entity."""
        return LibraryVolume(
            id=row["id"],
            title=row["title"],
            folder_path=Path(row["folder_path"]),
            cover_image_path=Path(row["cover_image_path"]),
            date_added=row["date_added"],
            last_opened=row["last_opened"],
        )
