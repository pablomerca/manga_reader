from pathlib import Path

import pytest

from manga_reader.io import DatabaseManager


@pytest.fixture
def manager(tmp_path):
    db_path = tmp_path / "vocab.db"
    db_manager = DatabaseManager(db_path)
    db_manager.ensure_schema()
    yield db_manager
    db_manager.close()


def test_schema_created(manager):
    cur = manager.connection.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    table_names = {row["name"] for row in cur.fetchall()}
    assert {"tracked_words", "manga_volumes", "word_appearances"}.issubset(
        table_names
    )


def test_upsert_tracked_word_is_idempotent(manager):
    first = manager.upsert_tracked_word("taberu", "taberu", "Verb")
    updated = manager.upsert_tracked_word("taberu", "taberu", "Ichidan")
    assert first.id == updated.id
    assert updated.part_of_speech == "Ichidan"


def test_upsert_volume_updates_existing(manager, tmp_path):
    volume_path = tmp_path / "naruto_vol_1"
    created = manager.upsert_volume(volume_path, "Naruto")
    updated = manager.upsert_volume(volume_path, "Naruto Updated")
    assert created.id == updated.id
    assert updated.name == "Naruto Updated"
    assert updated.path == volume_path.resolve()


def test_insert_word_appearance_is_idempotent(manager, tmp_path):
    word = manager.upsert_tracked_word("hashiru", "hashiru", "Verb")
    volume = manager.upsert_volume(tmp_path / "vol", "Vol")
    coords = {"x": 1, "y": 2, "width": 3, "height": 4}

    first = manager.insert_word_appearance(word.id, volume.id, 0, coords, "text")
    
    # Second insert of same appearance should raise ValueError (duplicate)
    with pytest.raises(ValueError, match="Word appearance already exists"):
        manager.insert_word_appearance(word.id, volume.id, 0, coords, "text")
    
    assert first is not None

    cur = manager.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM word_appearances")
    count = cur.fetchone()[0]
    assert count == 1


def test_list_tracked_words_returns_latest_first(manager):
    manager.upsert_tracked_word("hayai", "hayai", "Adj")
    manager.upsert_tracked_word("aoi", "aoi", "Adj")

    ordered = manager.list_tracked_words()
    lemmas = [word.lemma for word in ordered]
    assert lemmas[:2] == ["aoi", "hayai"]


def test_list_appearances_for_word_includes_volume_info(manager, tmp_path):
    word = manager.upsert_tracked_word("yomu", "yomu", "Verb")
    volume = manager.upsert_volume(tmp_path / "vol2", "Vol2")
    coords = {"x": 5, "y": 6, "width": 7, "height": 8}
    manager.insert_word_appearance(word.id, volume.id, 5, coords, "sentence")

    appearances = manager.list_appearances_for_word(word.id)
    assert len(appearances) == 1
    appearance = appearances[0]
    assert appearance.page_index == 5
    assert appearance.volume_name == volume.name
    assert appearance.volume_path == volume.path
    assert appearance.crop_coordinates["width"] == 7
