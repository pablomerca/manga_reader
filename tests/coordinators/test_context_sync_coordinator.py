"""Tests for ContextSyncCoordinator."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from manga_reader.coordinators.context_sync_coordinator import ContextSyncCoordinator
from manga_reader.core import MangaPage, MangaVolume, OCRBlock
from manga_reader.io import DatabaseManager
from manga_reader.services import VocabularyService


class FakeMorphology:
    """Simple morphology stub that returns a fixed lemma for any text."""

    def __init__(self, lemma: str | None = None):
        self._lemma = lemma or "tracked"

    def tokenize(self, text: str):
        class Token:
            def __init__(self, lemma: str):
                self.surface = lemma
                self.lemma = lemma

        return [Token(self._lemma)] if text else []


@pytest.fixture
def vocabulary_service(tmp_path):
    db_path = tmp_path / "vocab.db"
    db = DatabaseManager(db_path)
    db.ensure_schema()
    return VocabularyService(db, FakeMorphology("placeholder"))


@pytest.fixture
def sample_volume(tmp_path):
    volume_path = tmp_path / "vol"
    volume_path.mkdir()
    pages = [
        MangaPage(
            page_number=0,
            image_path=volume_path / "0001.jpg",
            width=100,
            height=200,
            ocr_blocks=[OCRBlock(x=1, y=2, width=10, height=20, text_lines=["text"])],
        )
    ]
    return MangaVolume(title="Vol", volume_path=volume_path, pages=pages)


@pytest.fixture
def main_window():
    window = MagicMock()
    window.show_error = MagicMock()
    window.show_info = MagicMock()
    window.show_question = MagicMock(return_value=True)
    return window


def test_sync_requires_volume(main_window, vocabulary_service):
    coordinator = ContextSyncCoordinator(
        main_window=main_window,
        vocabulary_service=vocabulary_service,
        morphology_service=FakeMorphology(),
    )

    coordinator.synchronize_current_volume()

    main_window.show_error.assert_called_once()


def test_sync_no_tracked_words(main_window, vocabulary_service, sample_volume):
    coordinator = ContextSyncCoordinator(
        main_window=main_window,
        vocabulary_service=vocabulary_service,
        morphology_service=FakeMorphology(),
    )
    coordinator.set_volume(sample_volume)

    coordinator.synchronize_current_volume()

    main_window.show_info.assert_called_once()
    main_window.show_question.assert_not_called()


def test_sync_records_new_appearances(main_window, vocabulary_service, sample_volume):
    tracked = vocabulary_service._db.upsert_tracked_word("tracked", "", "Noun")
    coordinator = ContextSyncCoordinator(
        main_window=main_window,
        vocabulary_service=vocabulary_service,
        morphology_service=FakeMorphology("tracked"),
    )
    coordinator.set_volume(sample_volume)

    coordinator.synchronize_current_volume()

    appearances = vocabulary_service.list_appearances(tracked.id)
    assert len(appearances) == 1
    assert appearances[0].page_index == 0
    # Should show completion info when new appearances are found
    assert any("Context Synchronization Complete" in call.args[0] for call in main_window.show_info.call_args_list)


def test_sync_is_idempotent(main_window, vocabulary_service, sample_volume):
    vocabulary_service._db.upsert_tracked_word("tracked", "", "Noun")
    coordinator = ContextSyncCoordinator(
        main_window=main_window,
        vocabulary_service=vocabulary_service,
        morphology_service=FakeMorphology("tracked"),
    )
    coordinator.set_volume(sample_volume)

    coordinator.synchronize_current_volume()
    main_window.show_info.reset_mock()
    coordinator.synchronize_current_volume()

    # Second run should report no new appearances
    assert any("No new context appearances" in call.args[1] for call in main_window.show_info.call_args_list)
