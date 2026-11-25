"""明示的に指定したSQLiteスナップショットから、空の共有DBに移す管理機能。"""

from contextlib import closing, contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3

from sqlalchemy import JSON, create_engine, func, inspect, insert, null, select, text
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

from caliboo_api.db import (
    lock_shared_initialization, require_empty_shared_db, shared_engine, validate_shared_schema,
)
from caliboo_api.models import Base


def _read_only_sqlite(path: Path):
    return sqlite3.connect(path.resolve(strict=True).as_uri() + "?mode=ro", uri=True)


def snapshot_sqlite(source: Path, destination: Path) -> None:
    """SQLiteのオンラインバックアップAPIで一貫性のある単一ファイルを作成する。"""
    with closing(_read_only_sqlite(source)) as original:
        # 既存ファイル(元DBを含む)はいかなる場合も上書きしない。所有者以外は読めない。
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        try:
            with closing(sqlite3.connect(destination)) as target:
                original.backup(target)
                if target.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                    raise RuntimeError("スナップショットの整合性検査に失敗しました。")
        except BaseException:
            destination.unlink()
            raise


@contextmanager
def snapshot_connection(snapshot: Path):
    engine = create_engine("sqlite://", creator=lambda: _read_only_sqlite(snapshot),
                           poolclass=NullPool, hide_parameters=True)
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA query_only=ON")
            connection.exec_driver_sql("BEGIN")
            _validate_source(connection)
            yield connection
    finally:
        engine.dispose()


def _validate_source(connection) -> None:
    if connection.exec_driver_sql("PRAGMA integrity_check").scalar() != "ok":
        raise RuntimeError("SQLiteの整合性検査に失敗しました。")
    if connection.exec_driver_sql("PRAGMA foreign_key_check").first() is not None:
        raise RuntimeError("SQLiteに外部キー不整合があります。元データを確認してください。")
    inspector = inspect(connection)
    if set(inspector.get_table_names()) != set(Base.metadata.tables):
        raise RuntimeError("SQLiteのテーブル構成が現行版と異なります。")
    for table in Base.metadata.sorted_tables:
        if {c["name"] for c in inspector.get_columns(table.name)} != set(table.c.keys()):
            raise RuntimeError(f"SQLiteの列構成が現行版と異なります: {table.name}")


def _rows(connection, table):
    # SQLのNULLとJSONのnullを区別して引き継ぎ、同じ区別で検証する。
    json_columns = [c for c in table.c if isinstance(c.type, JSON)]
    flags = [column.is_(None).label(f"_migration_null_{i}")
             for i, column in enumerate(json_columns)]
    for row in connection.execute(select(table, *flags)).mappings():
        values = {column.name: row[column.name] for column in table.c}
        sql_nulls = [column.name for i, column in enumerate(json_columns)
                     if row[f"_migration_null_{i}"]]
        yield values, sql_nulls


def _copy_table(source, target, table) -> None:
    for values, sql_nulls in _rows(source, table):
        for column in table.c:
            if isinstance(column.type, JSON) and values[column.name] is None:
                values[column.name] = null() if column.name in sql_nulls else JSON.NULL
        target.execute(insert(table).values(values))


def _fingerprint(connection, table) -> tuple[int, str]:
    # 日本語や照合順序の違いでも一致判定できるよう、標準化した全行を比較する。
    rows = sorted(json.dumps([row, sorted(nulls)], ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False)
                  for row, nulls in _rows(connection, table))
    hasher = hashlib.sha256()
    for row in rows:
        hasher.update(row.encode("utf-8"))
        hasher.update(b"\n")
    return len(rows), hasher.hexdigest()


def _sequence_floors(source):
    sqlite_sequence = {}
    if source.exec_driver_sql(
        "SELECT 1 FROM sqlite_master WHERE name='sqlite_sequence'"
    ).first():
        sqlite_sequence = dict(source.exec_driver_sql(
            "SELECT name, seq FROM sqlite_sequence").all())
    for table in Base.metadata.sorted_tables:
        column = table.autoincrement_column
        if column is not None:
            highest = source.execute(select(func.max(column))).scalar_one() or 0
            # !NOTE: AUTOINCREMENTの削除済みIDも再利用させない。
            yield table, column, max(0, highest, sqlite_sequence.get(table.name, 0))


def _sequence_name(connection, table, column) -> str:
    name = connection.execute(text("SELECT pg_get_serial_sequence(:table, :column)"),
                              {"table": table.name, "column": column.name}).scalar_one()
    if not name:
        raise RuntimeError(f"採番シーケンスがありません: {table.name}")
    return name


def _set_sequences(source, target) -> None:
    for table, column, highest in _sequence_floors(source):
        sequence = _sequence_name(target, table, column)
        target.execute(text("SELECT setval(CAST(:sequence AS regclass), :value, :called)"),
                       {"sequence": sequence, "value": max(1, highest), "called": highest > 0})


def _verify(source, target) -> dict[str, int]:
    validate_shared_schema(target)
    counts = {}
    for table in Base.metadata.sorted_tables:
        before = _fingerprint(source, table)
        after = _fingerprint(target, table)
        if before != after:
            raise RuntimeError(f"件数または内容が一致しません: {table.name}")
        counts[table.name] = before[0]
    _verify_sequences(source, target)
    return counts


def _verify_sequences(source, target) -> None:
    for table, column, highest in _sequence_floors(source):
        sequence = _sequence_name(target, table, column)
        last = target.execute(
            text("SELECT pg_sequence_last_value(CAST(:sequence AS regclass))"),
            {"sequence": sequence},
        ).scalar_one()
        if highest and (last is None or last < highest):
            raise RuntimeError(f"採番シーケンスが一致しません: {table.name}")


def migrate_sqlite(snapshot: Path, target_url: URL) -> dict[str, int]:
    """ソースは読み取り専用。空DBにのみ一括反映し、不一致ならDDLごと巻き戻す。"""
    engine = shared_engine(target_url)
    try:
        with snapshot_connection(snapshot) as source, engine.begin() as target:
            lock_shared_initialization(target)
            require_empty_shared_db(target)
            Base.metadata.create_all(target)
            for table in Base.metadata.sorted_tables:
                _copy_table(source, target, table)
            _set_sequences(source, target)
            return _verify(source, target)
    finally:
        engine.dispose()


def verify_migration(snapshot: Path, target_url: URL) -> dict[str, int]:
    engine = shared_engine(target_url)
    try:
        with snapshot_connection(snapshot) as source, engine.connect() as target:
            target = target.execution_options(isolation_level="REPEATABLE READ")
            with target.begin():
                target.execute(text("SET TRANSACTION READ ONLY"))
                return _verify(source, target)
    finally:
        engine.dispose()
