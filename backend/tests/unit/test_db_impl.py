import os
import sqlite3

import pytest

import caliboo_api.db as db
from caliboo_api.models import Department


def test_init_engine_creates_parent_dir(tmp_path):
    nested_path = tmp_path / "nested" / "dir" / "test.db"
    assert not nested_path.parent.exists()

    db.init_engine(str(nested_path))

    assert nested_path.parent.exists()


def test_get_session_raises_when_not_initialized(monkeypatch):
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)

    with pytest.raises(RuntimeError):
        next(db.get_session())


def test_bootstrap_db_raises_when_not_initialized(monkeypatch):
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)

    with pytest.raises(RuntimeError):
        db.bootstrap_db()


def test_session_scope_yields_usable_session(tmp_path):
    db_path = str(tmp_path / "session_scope.db")
    db.init_engine(db_path)
    db.bootstrap_db()

    with db.session_scope() as session:
        assert session.query(Department).first() is not None

    assert os.path.exists(db_path)


def test_bootstrap_db_raises_when_legacy_schema_is_detected(tmp_path):
    """`users`テーブル導入前のスキーマ(`home_profile`に`user_id`列が無く、`users`テーブルも無い)の
    DBファイルへ対して`bootstrap_db()`を呼ぶと、DB削除を促すRuntimeErrorで失敗する。
    """
    db_path = str(tmp_path / "legacy.db")
    connection = sqlite3.connect(db_path)
    connection.execute(
        "CREATE TABLE departments ("
        "id TEXT PRIMARY KEY, name TEXT, icon TEXT, color TEXT, knowledge_count INTEGER)"
    )
    connection.execute("INSERT INTO departments VALUES ('dev', '開発課', 'icon', 'color', 1)")
    connection.execute(
        "CREATE TABLE home_profile ("
        "id INTEGER PRIMARY KEY, user_name TEXT, user_streak_days INTEGER, "
        "hero_message TEXT, certification_id INTEGER)"
    )
    connection.commit()
    connection.close()

    db.init_engine(db_path)

    with pytest.raises(RuntimeError, match="caliboo.db"):
        db.bootstrap_db()


def test_bootstrap_db_does_not_raise_for_brand_new_empty_database(tmp_path):
    """新規(空)のDBファイルは、`departments`が未シードのため旧スキーマ判定に該当しない。"""
    db_path = str(tmp_path / "brand_new.db")
    db.init_engine(db_path)

    db.bootstrap_db()

    with db.session_scope() as session:
        assert session.query(Department).count() == 6
