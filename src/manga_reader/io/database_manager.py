"""SQLite-backed vocabulary tracking persistence."""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from manga_reader.core import MangaVolumeEntry, TrackedWord, WordAppearance


class DatabaseManager:
    """Owns SQLite connection, schema, and vocabulary persistence helpers."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON;")

    def ensure_schema(self) -> None:
        """Create tables and indexes if they do not exist."""
        cur = self.connection.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tracked_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lemma TEXT NOT NULL,
                reading TEXT NOT NULL DEFAULT '',
                part_of_speech TEXT NOT NULL DEFAULT '',
                date_added TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(lemma, reading)
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS manga_volumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS word_appearances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word_id INTEGER NOT NULL,
                volume_id INTEGER NOT NULL,
                page_index INTEGER NOT NULL,
                crop_coordinates TEXT NOT NULL,
                sentence_text TEXT NOT NULL DEFAULT '',

                FOREIGN KEY(word_id) REFERENCES tracked_words(id) ON DELETE CASCADE,
                FOREIGN KEY(volume_id) REFERENCES manga_volumes(id) ON DELETE CASCADE,
                UNIQUE(word_id, volume_id, page_index, crop_coordinates)
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tracked_words_lemma
            ON tracked_words(lemma);
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_word_appearances_word
            ON word_appearances(word_id);
            """
        )
        self.connection.commit()

    def upsert_tracked_word(
        self, lemma: str, reading: str = "", part_of_speech: str = ""
    ) -> TrackedWord:
        lemma = lemma.strip()
        reading = (reading or "").strip()
        part_of_speech = part_of_speech or ""
        cur = self.connection.cursor()
        cur.execute(
            """
            INSERT INTO tracked_words (lemma, reading, part_of_speech)
            VALUES (?, ?, ?)
            ON CONFLICT(lemma, reading) DO UPDATE SET
                part_of_speech = excluded.part_of_speech
            """,
            (lemma, reading, part_of_speech),
        )
        self.connection.commit()
        return self._get_tracked_word(lemma, reading)

    def upsert_volume(self, path: Path, name: Optional[str] = None) -> MangaVolumeEntry:
        path_obj = Path(path).resolve()
        volume_name = name or path_obj.name
        cur = self.connection.cursor()
        cur.execute(
            """
            INSERT INTO manga_volumes (path, name)
            VALUES (?, ?)
            ON CONFLICT(path) DO UPDATE SET
                name = excluded.name
            """,
            (str(path_obj), volume_name),
        )
        self.connection.commit()
        return self._get_volume(path_obj)

    def insert_word_appearance(
        self,
        word_id: int,
        volume_id: int,
        page_index: int,
        crop_coordinates: Dict[str, float],
        sentence_text: str,
    ) -> Optional[WordAppearance]:
        coords_json = json.dumps(crop_coordinates, ensure_ascii=True)
        cur = self.connection.cursor()
        appearance_id: Optional[int]
        try:
            cur.execute(
                """
                INSERT INTO word_appearances (
                    word_id, volume_id, page_index, crop_coordinates, sentence_text
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (word_id, volume_id, page_index, coords_json, sentence_text or ""),
            )
            self.connection.commit()
            appearance_id = cur.lastrowid
        except sqlite3.IntegrityError:
            appearance_id = None
        if appearance_id is None:
            cur.execute(
                """
                SELECT id FROM word_appearances
                WHERE word_id = ? AND volume_id = ? AND page_index = ? AND crop_coordinates = ?
                """,
                (word_id, volume_id, page_index, coords_json),
            )
            row = cur.fetchone()
            appearance_id = row["id"] if row else None
        return self._get_word_appearance_by_id(appearance_id) if appearance_id else None

    def list_tracked_words(self) -> List[TrackedWord]:
        cur = self.connection.cursor()
        cur.execute(
            """
            SELECT id, lemma, reading, part_of_speech, date_added
            FROM tracked_words
            ORDER BY date_added DESC, id DESC
            """
        )
        rows = cur.fetchall()
        return [self._row_to_tracked_word(row) for row in rows]

    def list_appearances_for_word(self, word_id: int) -> List[WordAppearance]:
        cur = self.connection.cursor()
        cur.execute(
            """
            SELECT
                wa.id,
                wa.word_id,
                wa.volume_id,
                wa.page_index,
                wa.crop_coordinates,
                wa.sentence_text,
                mv.name AS volume_name,
                mv.path AS volume_path
            FROM word_appearances wa
            JOIN manga_volumes mv ON wa.volume_id = mv.id
            WHERE wa.word_id = ?
            ORDER BY wa.volume_id ASC, wa.page_index ASC, wa.id ASC
            """,
            (word_id,),
        )
        rows = cur.fetchall()
        return [self._row_to_word_appearance(row) for row in rows]

    def close(self) -> None:
        self.connection.close()

    def _get_tracked_word(self, lemma: str, reading: str) -> TrackedWord:
        cur = self.connection.cursor()
        cur.execute(
            """
            SELECT id, lemma, reading, part_of_speech, date_added
            FROM tracked_words
            WHERE lemma = ? AND reading = ?
            """,
            (lemma, reading),
        )
        row = cur.fetchone()
        return self._row_to_tracked_word(row)

    def _get_volume(self, path: Path) -> MangaVolumeEntry:
        cur = self.connection.cursor()
        cur.execute(
            """
            SELECT id, path, name FROM manga_volumes WHERE path = ?
            """,
            (str(path),),
        )
        row = cur.fetchone()
        return self._row_to_volume(row)

    def _get_word_appearance_by_id(self, appearance_id: int) -> Optional[WordAppearance]:
        cur = self.connection.cursor()
        cur.execute(
            """
            SELECT
                wa.id,
                wa.word_id,
                wa.volume_id,
                wa.page_index,
                wa.crop_coordinates,
                wa.sentence_text,
                mv.name AS volume_name,
                mv.path AS volume_path
            FROM word_appearances wa
            JOIN manga_volumes mv ON wa.volume_id = mv.id
            WHERE wa.id = ?
            """,
            (appearance_id,),
        )
        row = cur.fetchone()
        return self._row_to_word_appearance(row) if row else None

    @staticmethod
    def _row_to_tracked_word(row: sqlite3.Row) -> TrackedWord:
        return TrackedWord(
            id=row["id"],
            lemma=row["lemma"],
            reading=row["reading"],
            part_of_speech=row["part_of_speech"],
            date_added=row["date_added"],
        )

    @staticmethod
    def _row_to_volume(row: sqlite3.Row) -> MangaVolumeEntry:
        return MangaVolumeEntry(
            id=row["id"],
            path=Path(row["path"]),
            name=row["name"],
        )

    @staticmethod
    def _row_to_word_appearance(row: sqlite3.Row) -> WordAppearance:
        coords_raw = row["crop_coordinates"] or "{}"
        coords = json.loads(coords_raw)
        volume_path_value = row["volume_path"] if "volume_path" in row.keys() else None
        return WordAppearance(
            id=row["id"],
            word_id=row["word_id"],
            volume_id=row["volume_id"],
            page_index=row["page_index"],
            crop_coordinates=coords,
            sentence_text=row["sentence_text"],
            volume_name=row["volume_name"] if "volume_name" in row.keys() else None,
            volume_path=Path(volume_path_value) if volume_path_value else None,
        )
